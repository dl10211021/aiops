import argparse
import winrm
import json
import base64

class ScriptBank:
    """
    Collection of robust PowerShell scripts for common administrative tasks.
    Using predefined scripts avoids escaping issues and syntax errors during generation.
    """
    
    @staticmethod
    def get_software():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
$paths = @(
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

$installed = Get-ItemProperty $paths | 
    Where-Object { $_.DisplayName -ne $null } |
    Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
    Sort-Object DisplayName

$installed | ConvertTo-Json -Compress
"""

    @staticmethod
    def get_logs(hours=24, log_name='System', entry_type='Error,Warning'):
        return f"""
$ErrorActionPreference = 'SilentlyContinue'
$since = (Get-Date).AddHours(-{hours})
$logs = Get-EventLog -LogName "{log_name}" -EntryType {entry_type} -After $since -Newest 50
$result = foreach ($l in $logs) {{
    @{{ Type='{log_name}'; Level=$l.EntryType; Time=$l.TimeGenerated; Source=$l.Source; Msg=$l.Message }}
}}
$result | ConvertTo-Json -Compress
"""

    @staticmethod
    def get_services(filter_name="*"):
        return f"""
$ErrorActionPreference = 'SilentlyContinue'
$filter = "{filter_name}"
Get-Service | 
    Where-Object {{ $_.DisplayName -like $filter -or $_.Name -like $filter }} |
    Select-Object Name, DisplayName, Status, StartType, ServiceName |
    Sort-Object Status |
    ConvertTo-Json -Compress
"""

    @staticmethod
    def get_info():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, LastBootUpTime, FreePhysicalMemory, TotalVisibleMemorySize, OSArchitecture
$cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object Average
$disks = Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='UsedGB';E={[math]::round($_.Used/1GB,2)}}, @{N='FreeGB';E={[math]::round($_.Free/1GB,2)}}, @{N='TotalGB';E={[math]::round(($_.Used + $_.Free)/1GB,2)}}

@{
    OS = $os
    CPU_Load = $cpu.Average
    Disks = $disks
} | ConvertTo-Json -Compress
"""

    @staticmethod
    def stop_service(service_name):
        return f"""
$ErrorActionPreference = 'Stop'
try {{
    $svc = Get-Service -Name "{service_name}" -ErrorAction Stop
    if ($svc.Status -eq 'Running') {{
        Stop-Service -Name "{service_name}" -Force
        Write-Output "Service {service_name} stopped."
    }} else {{
        Write-Output "Service {service_name} is already $($svc.Status)."
    }}
}} catch {{
    Write-Error $_.Exception.Message
}}
"""

    @staticmethod
    def get_defender():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
$status = Get-MpComputerStatus | Select-Object AMRunningMode, RealTimeProtectionEnabled, IsTamperProtected, AntivirusEnabled, AntispywareEnabled
$status | ConvertTo-Json -Compress
"""

    @staticmethod
    def get_av():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
# Common AV service keywords
$keywords = "*Cortex*", "*Cyver*", "*Symantec*", "*McAfee*", "*Sophos*", "*Trend*", "*Sentinel*", "*Kaspersky*", "*Eset*", "*Bitdefender*", "*Avast*", "*360*", "*ThreatBook*", "*tbSvc*", "*Trellix*", "*Huorong*"
Get-Service | 
    Where-Object { 
        $n = $_.Name; $d = $_.DisplayName;
        ($keywords | Where-Object { $n -like $_ -or $d -like $_ })
    } |
    Select-Object Name, DisplayName, Status, StartType |
    ConvertTo-Json -Compress
"""

    @staticmethod
    def get_top_processes(top=15):
        return f"""
$ErrorActionPreference = 'SilentlyContinue'
Get-Process | 
    Sort-Object CPU -Descending | 
    Select-Object -First {top} | 
    Select-Object Id, ProcessName, Path, @{{N='CPU(s)';E={{$_.CPU.ToString("N1")}}}}, @{{N='Memory(MB)';E={{[math]::round($_.WS/1MB,1)}}}} |
    ConvertTo-Json -Compress
"""

    @staticmethod
    def get_security_audit():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'

# 1. Local Users
$users = Get-LocalUser | Select-Object Name, Enabled, LastLogon, Description

# 2. Local Admins
$admins = Get-LocalGroupMember -Group 'Administrators' | Select-Object Name, ObjectClass

# 3. Listening Ports (External)
# Filter for IPv4 (0.0.0.0) or IPv6 (::)
$ports = Get-NetTCPConnection -State Listen | 
    Where-Object { $_.LocalAddress -eq '0.0.0.0' -or $_.LocalAddress -eq '::' } |
    Select-Object LocalAddress, LocalPort, OwningProcess, @{N='Process';E={(Get-Process -Id $_.OwningProcess).ProcessName}}

@{
    Users = $users
    Admins = $admins
    OpenPorts = $ports
} | ConvertTo-Json -Compress
"""

    @staticmethod
    def get_veeam_status():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
$services = Get-Service | Where-Object { $_.DisplayName -like '*Veeam*' } | Select-Object Name, DisplayName, Status, StartType
# Check for basic SQL connectivity if Veeam SQL instance exists
$sql = Get-Service | Where-Object { $_.Name -like '*VEEAMSQL*' } | Select-Object Name, Status

@{
    VeeamServices = $services
    VeeamSQL = $sql
} | ConvertTo-Json -Compress
"""

    @staticmethod
    def check_disk_health():
        return r"""
$ErrorActionPreference = 'SilentlyContinue'
$logical = Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, VolumeName, FileSystem, @{N='SizeGB';E={[math]::round($_.Size/1GB,2)}}, @{N='FreeGB';E={[math]::round($_.FreeSpace/1GB,2)}}
$physical = Get-CimInstance Win32_DiskDrive | Select-Object DeviceID, Model, Status, MediaType, Size
@{
    Logical = $logical
    Physical = $physical
} | ConvertTo-Json -Compress
"""

    @staticmethod
    def find_large_files(path="C:\\", min_size_mb=1000):
        return f"""
$ErrorActionPreference = 'SilentlyContinue'
# Safe approach: List top level folder sizes in the given path
$startPath = "{path}"
$folders = Get-ChildItem -Path $startPath -Directory -ErrorAction SilentlyContinue
$result = foreach ($folder in $folders) {{
    $size = (Get-ChildItem -Path $folder.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{{
        Name = $folder.Name
        FullPath = $folder.FullName
        SizeMB = [math]::round($size / 1MB, 2)
    }}
}}
$result | Sort-Object SizeMB -Descending | Select-Object -First 20 | ConvertTo-Json -Compress
"""

def encode_powershell(script):
    """
    Encodes a PowerShell script into a Base64 string of UTF-16LE bytes.
    This bypasses shell escaping issues.
    """
    return base64.b64encode(script.encode('utf_16_le')).decode('utf-8')

def run_winrm_command(target, username, password, command, use_base64=True):
    try:
        session = winrm.Session(target, auth=(username, password), transport='ntlm')
        
        stdout_clean = ""
        stderr_clean = ""
        
        # 1. Primary Execution
        if use_base64:
            encoded_cmd = encode_powershell(command)
            # Use 'run_cmd' to invoke powershell.exe with encoded block
            result = session.run_cmd(f"powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded_cmd}")
        else:
            if command.lower().startswith("cmd") or command.lower().startswith("wmic"):
                 result = session.run_cmd(command)
            else:
                 result = session.run_ps(command)
        
        stdout_clean = result.std_out.decode('utf-8', errors='ignore').strip()
        stderr_clean = result.std_err.decode('utf-8', errors='ignore').strip()

        # 2. Auto-Fallback Logic
        if use_base64 and (
            (result.status_code == 0 and not stdout_clean and not stderr_clean) or
            ("is not recognized" in stderr_clean) or
            ("encoded command" in stderr_clean)
        ):
            fallback_msg = "[WARN] Base64 execution failed or returned empty. Retrying with Raw Mode..."
            result_retry = session.run_ps(command)
            stdout_clean = result_retry.std_out.decode('utf-8', errors='ignore').strip()
            stderr_clean_retry = result_retry.std_err.decode('utf-8', errors='ignore').strip()
            
            result = result_retry
            if stderr_clean_retry:
                stderr_clean = fallback_msg + "\n" + stderr_clean_retry
            else:
                stderr_clean = fallback_msg

        parsed_output = None
        if stdout_clean.strip().startswith("{") or stdout_clean.strip().startswith("["):
            try:
                json_str = stdout_clean
                idx_obj = json_str.find('{')
                idx_arr = json_str.find('[')
                
                start_idx = -1
                if idx_obj != -1 and idx_arr != -1:
                    start_idx = min(idx_obj, idx_arr)
                elif idx_obj != -1:
                    start_idx = idx_obj
                elif idx_arr != -1:
                    start_idx = idx_arr
                
                if start_idx != -1:
                    json_str = json_str[start_idx:]
                    json_str = json_str.rstrip()
                    while json_str and json_str[-1] not in ['}', ']']:
                        json_str = json_str[:-1]
                        
                    parsed_output = json.loads(json_str)
            except json.JSONDecodeError:
                pass

        output = {
            "status": "success" if result.status_code == 0 else "error",
            "exit_code": result.status_code,
            "stdout": stdout_clean,
            "stderr": stderr_clean,
            "data": parsed_output
        }
        
        return output

    except Exception as e:
        return {
            "status": "connection_error",
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description='Execute PowerShell on Remote Windows via WinRM (Optimized)')
    parser.add_argument('--target', required=True, help='Target IP or Hostname')
    parser.add_argument('--user', required=True, help='Username')
    parser.add_argument('--password', required=True, help='Password')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--command', help='Raw PowerShell command to execute')
    group.add_argument('--action', choices=[
        'inventory', 'software', 'logs', 'services', 'stop-service', 
        'defender', 'av', 'process', 'security-audit', 'veeam-status', 'disk-health', 'folder-size'
    ], help='Pre-defined action to run')
    
    parser.add_argument('--filter', help='Filter string for services action')
    parser.add_argument('--service-name', help='Service name for stop-service action')
    parser.add_argument('--path', default='C:\\', help='Path for folder-size action')
    parser.add_argument('--no-base64', action='store_true', help='Disable Base64 encoding for commands')

    args = parser.parse_args()

    script_content = ""
    if args.command:
        script_content = args.command
    elif args.action == 'inventory':
        script_content = ScriptBank.get_info()
    elif args.action == 'software':
        script_content = ScriptBank.get_software()
    elif args.action == 'logs':
        script_content = ScriptBank.get_logs()
    elif args.action == 'services':
        filter_val = args.filter if args.filter else "*"
        script_content = ScriptBank.get_services(filter_val)
    elif args.action == 'stop-service':
        if not args.service_name:
            print(json.dumps({"status": "error", "error": "--service-name required"}))
            return
        script_content = ScriptBank.stop_service(args.service_name)
    elif args.action == 'defender':
        script_content = ScriptBank.get_defender()
    elif args.action == 'av':
        script_content = ScriptBank.get_av()
    elif args.action == 'process':
        script_content = ScriptBank.get_top_processes()
    elif args.action == 'security-audit':
        script_content = ScriptBank.get_security_audit()
    elif args.action == 'veeam-status':
        script_content = ScriptBank.get_veeam_status()
    elif args.action == 'disk-health':
        script_content = ScriptBank.check_disk_health()
    elif args.action == 'folder-size':
        script_content = ScriptBank.find_large_files(args.path)

    use_b64 = not args.no_base64
    result = run_winrm_command(args.target, args.user, args.password, script_content, use_base64=use_b64)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()