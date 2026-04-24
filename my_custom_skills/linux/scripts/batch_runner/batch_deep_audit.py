#!/usr/bin/env python3
import paramiko
import argparse
import getpass
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Recommended Baselines ---
BASELINE = {
    "vm.swappiness": 10,
    "fs.file-max": 1000000,
    "ulimit": 65535,
    "net.core.somaxconn": 1024,
    "net.ipv4.ip_local_port_range_start": 10000 # Should be lower, e.g. < 30000
}

AUDIT_SCRIPT = r"""
export LANG=C
echo "===LIMITS==="
# Check limits.conf for explicit settings
grep -E "^\*\s+(soft|hard)\s+nofile" /etc/security/limits.conf || echo "NO_LIMITS_CONF"
# Check current shell (for reference, though SSH might differ from service)
ulimit -n

echo "===SYSCTL==="
sysctl vm.swappiness
sysctl fs.file-max
sysctl net.core.somaxconn
sysctl net.ipv4.ip_local_port_range
sysctl net.ipv4.tcp_max_syn_backlog
sysctl net.ipv4.tcp_tw_reuse

echo "===LOGS==="
# Get logs from last 30 minutes, excluding collectd
# Try journalctl first (Systemd systems)
if command -v journalctl >/dev/null; then
    journalctl -p 3 -n 20 --since "30 min ago" | grep -v "collectd"
else
    # Fallback to messages
    LOG=/var/log/messages
    [ -f /var/log/syslog ] && LOG=/var/log/syslog
    tail -n 200 $LOG | grep -iE "error|fail|critical" | grep -v "collectd" | tail -n 10
fi
"""

def check_server(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    result = {
        "ip": ip,
        "recommendations": [],
        "logs": [],
        "current_vals": {}
    }

    try:
        client.connect(ip, username=user, password=pwd, timeout=8)
        stdin, stdout, stderr = client.exec_command(AUDIT_SCRIPT)
        output = stdout.read().decode('utf-8', errors='ignore')
        
        # --- Parsing ---
        lines = output.splitlines()
        section = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("==="):
                section = line.strip("=")
                continue
            
            if section == "LIMITS":
                if line.isdigit(): # ulimit -n output
                    val = int(line)
                    result["current_vals"]["ulimit"] = val
                    if val < BASELINE["ulimit"]:
                        result["recommendations"].append(f"Increase ulimit (Current: {val}, Rec: {BASELINE['ulimit']}+)")
                elif "soft" in line or "hard" in line:
                    result["current_vals"]["limits.conf"] = "Configured"

            elif section == "SYSCTL":
                if "=" in line:
                    key, val_str = line.split("=", 1)
                    key = key.strip()
                    val_str = re.sub(r'\s+', ' ', val_str.strip()) # Handle multiple spaces
                    
                    if key == "vm.swappiness":
                        val = int(val_str)
                        result["current_vals"][key] = val
                        if val > BASELINE["vm.swappiness"]:
                             result["recommendations"].append(f"Lower vm.swappiness (Current: {val}, Rec: 10)")
                    
                    elif key == "fs.file-max":
                        val = int(val_str)
                        result["current_vals"][key] = val
                        if val < BASELINE["fs.file-max"]:
                            result["recommendations"].append(f"Increase fs.file-max (Current: {val}, Rec: 1M+)")
                            
                    elif key == "net.core.somaxconn":
                        val = int(val_str)
                        result["current_vals"][key] = val
                        if val < BASELINE["net.core.somaxconn"]:
                            result["recommendations"].append(f"Increase net.core.somaxconn (Current: {val}, Rec: 1024+)")
                    
                    elif key == "net.ipv4.ip_local_port_range":
                        # ex: 32768 60999
                        parts = val_str.split()
                        start = int(parts[0])
                        end = int(parts[-1])
                        result["current_vals"][key] = val_str
                        if start > 15000: # If start is high (32768 default), range is small
                            result["recommendations"].append(f"Widen Port Range (Current: {val_str}, Rec: 10000 65000)")

            elif section == "LOGS":
                if len(line) > 5:
                    result["logs"].append(line)

        # Check if limits.conf was missing
        if "limits.conf" not in result["current_vals"] and result["current_vals"].get("ulimit", 0) < 65535:
             result["recommendations"].append("Configure /etc/security/limits.conf for high concurrency")

        client.close()

    except Exception as e:
        result["recommendations"].append(f"Error during check: {str(e)}")
    
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ips", nargs='+', required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=False)
    args = parser.parse_args()

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass("SSH Password: ")

    print(f"[*] Deep Auditing {len(args.ips)} servers (Files, Network, Kernel, Logs)...")
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_server, ip, args.user, pwd): ip for ip in args.ips}
        for future in as_completed(futures):
            results.append(future.result())

    # --- Print Summary ---
    print("\n" + "="*80)
    print(f"{'IP':<16} | {'Opt. Needed?':<12} | {'Recent Log Errors'}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: x['ip']):
        opt_needed = "YES" if r["recommendations"] else "NO"
        log_status = f"{len(r['logs'])} Found" if r['logs'] else "Clean"
        print(f"{r['ip']:<16} | {opt_needed:<12} | {log_status}")

    # --- Detail View ---
    for r in results:
        if r['recommendations'] or r['logs']:
            print(f"\n[>] Details for {r['ip']}:")
            
            if r['recommendations']:
                print("    Optimization Suggestions:")
                for rec in r['recommendations']:
                    print(f"      - {rec}")
            
            if r['logs']:
                print("    Recent Error Logs (Last 30m):")
                for l in r['logs']:
                    print(f"      ! {l}")

    print("\n[INFO] 'Opt. Needed' indicates system parameters are at defaults and could be tuned for high load.")

if __name__ == "__main__":
    main()
