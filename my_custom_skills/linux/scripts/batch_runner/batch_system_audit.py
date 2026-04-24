#!/usr/bin/env python3
import paramiko
import argparse
import re
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Audit Configuration ---
# Thresholds
DISK_THRESHOLD = 85
MEM_THRESHOLD = 90
LOAD_THRESHOLD = 0.7 # relative to cores (e.g. 0.7 * cores)

# Commands to run remotely
# We construct a single large shell command to minimize round-trips
AUDIT_CMD = r"""
export LANG=C
echo "===SYSTEM_INFO==="
hostname
cat /etc/redhat-release 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME
uptime
nproc

echo "===MEMORY==="
free -m

echo "===DISK==="
df -hP --exclude-type=tmpfs --exclude-type=devtmpfs

echo "===DNS_TEST==="
ping -c 1 -W 2 192.168.41.60 >/dev/null 2>&1 && echo "DNS_SERVER_REACHABLE" || echo "DNS_SERVER_UNREACHABLE"

echo "===LOG_ERRORS==="
# Check last 50 lines of messages/syslog for critical errors
LOG_FILE="/var/log/messages"
[ -f /var/log/syslog ] && LOG_FILE="/var/log/syslog"
grep -iE "oom-killer|segfault|call trace|temperature|hardware error|I/O error" $LOG_FILE 2>/dev/null | tail -n 5
dmesg | grep -iE "error|fail" | tail -n 5

echo "===PARAMETERS==="
sysctl vm.swappiness
cat /proc/sys/fs/file-max
ulimit -n

echo "===SECURITY==="
sestatus 2>/dev/null || echo "SELinux: N/A"
systemctl is-active firewalld 2>/dev/null || echo "Firewalld: Inactive"
"""

def get_ssh_client(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=pwd, timeout=8)
        return client
    except Exception:
        return None

def analyze_server(ip, user, pwd):
    client = get_ssh_client(ip, user, pwd)
    report = {
        "ip": ip,
        "status": "UNREACHABLE",
        "issues": [],
        "info": {},
        "raw_logs": ""
    }
    
    if not client:
        return report
    
    report["status"] = "ONLINE"
    
    try:
        stdin, stdout, stderr = client.exec_command(AUDIT_CMD)
        output = stdout.read().decode('utf-8', errors='ignore')
        client.close()
        
        # --- Parsing ---
        sections = output.split("===")
        data = {}
        for s in sections:
            lines = s.strip().splitlines()
            if not lines: continue
            header = lines[0] # The section name usually implies parsing strategy, but we split by "===" already so section name is removed or empty?
            # Actually split "===NAME===" leaves "NAME" in the list? No, split uses delimiter.
            # My command has `echo "===SECTION==="`.
            # output will be:
            # ===SYSTEM_INFO===
            # ...
            # ===MEMORY===
            # ...
        
        # Re-parse properly
        current_section = None
        for line in output.splitlines():
            if line.startswith("===") and line.endswith("==="):
                current_section = line.strip("=")
                data[current_section] = []
            elif current_section:
                data[current_section].append(line)

        # 1. System Info
        sys_info = data.get("SYSTEM_INFO", [])
        if len(sys_info) >= 4:
            report["info"]["hostname"] = sys_info[0]
            report["info"]["os"] = sys_info[1]
            report["info"]["uptime"] = sys_info[2]
            try:
                cores = int(sys_info[3])
            except:
                cores = 1
            report["info"]["cores"] = cores

            # Check Load
            load_match = re.search(r'load average: ([\d\.]+)', sys_info[2])
            if load_match:
                load_1min = float(load_match.group(1))
                if load_1min > (cores * LOAD_THRESHOLD):
                    report["issues"].append(f"High Load: {load_1min} (Cores: {cores})")

        # 2. Memory
        mem_info = data.get("MEMORY", [])
        if len(mem_info) >= 2:
            # Swap check
            # Mem:   15866        4643        4245 ...
            # Swap:   8191           0        8191
            for line in mem_info:
                if "Swap:" in line:
                    parts = line.split()
                    total_swap = int(parts[1])
                    used_swap = int(parts[2])
                    if total_swap > 0 and (used_swap / total_swap) > 0.5:
                         report["issues"].append(f"High Swap Usage: {used_swap}MB / {total_swap}MB")

        # 3. Disk
        disk_info = data.get("DISK", [])
        for line in disk_info[1:]: # Skip header
            parts = line.split()
            if len(parts) >= 5:
                # /dev/sda1 50G 45G 5G 90% /
                try:
                    usage_str = parts[-2].rstrip('%')
                    usage_pct = int(usage_str)
                    mount = parts[-1]
                    if usage_pct >= DISK_THRESHOLD:
                         report["issues"].append(f"Disk High Usage: {mount} is {usage_pct}%")
                except:
                    pass

        # 4. Network/DNS
        dns_info = data.get("DNS_TEST", [])
        if "DNS_SERVER_UNREACHABLE" in dns_info:
            report["issues"].append("DNS Server (192.168.41.60) Unreachable")

        # 5. Logs
        log_info = data.get("LOG_ERRORS", [])
        if log_info:
            report["issues"].append(f"Found {len(log_info)} critical log entries")
            report["raw_logs"] = "\n".join(log_info)

        # 6. Parameters (Optimization Checks)
        param_info = data.get("PARAMETERS", [])
        for line in param_info:
            if "vm.swappiness" in line:
                val = int(line.split('=')[-1].strip())
                if val > 10:
                    report["issues"].append(f"Optimization: vm.swappiness is {val} (Recommend 10 for Servers)")

        # 7. Security
        sec_info = data.get("SECURITY", [])
        for line in sec_info:
            if "SELinux status: enabled" in line or "Current mode: enforcing" in line:
                pass # Just info
            if "active (running)" in line and "firewalld" in line:
                 report["info"]["firewall"] = "On"
            
    except Exception as e:
        report["status"] = "ERROR"
        report["issues"].append(str(e))

    return report

def main():
    parser = argparse.ArgumentParser(description="Batch System Audit & Optimization Report")
    parser.add_argument("--ips", nargs='+', required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=False)
    args = parser.parse_args()

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass("SSH Password: ")

    print(f"[*] Auditing {len(args.ips)} servers...")
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze_server, ip, args.user, pwd): ip for ip in args.ips}
        for future in as_completed(futures):
            results.append(future.result())

    # --- Print Report ---
    print("\n" + "="*80)
    print(f"{'IP':<16} | {'Status':<8} | {'Hostname':<20} | {'Issues Count'}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: x['ip']):
        issue_cnt = len(r['issues'])
        status_color = r['status']
        print(f"{r['ip']:<16} | {status_color:<8} | {r['info'].get('hostname', 'N/A'):<20} | {issue_cnt}")

    print("="*80)
    
    # Detailed Issues
    issues_found = False
    for r in results:
        if r['issues']:
            issues_found = True
            print(f"\n[!] Issues on {r['ip']} ({r['info'].get('hostname', '')}):")
            for i in r['issues']:
                print(f"    - {i}")
            if r['raw_logs']:
                print("    --- Log Snippets ---")
                for l in r['raw_logs'].splitlines():
                    print(f"        {l}")

    if not issues_found:
        print("\n[+] No critical issues or warnings found. Systems look healthy.")

if __name__ == "__main__":
    main()
