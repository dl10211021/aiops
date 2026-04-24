#!/usr/bin/env python3
import paramiko
import argparse
import sys
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

AUDIT_SCRIPT = r"""
export LANG=C
echo "===LIMITS==="
ulimit -n
grep -HE "^\*\s+(soft|hard)\s+nofile" /etc/security/limits.conf /etc/security/limits.d/*.conf 2>/dev/null

echo "===SYSCTL==="
sysctl vm.swappiness
sysctl fs.file-max

echo "===RESOURCE==="
free -m
uptime

echo "===BLOATWARE==="
# Check for common GUI/Desktop services that waste memory
systemctl is-active gdm gnome-shell packagekit cups avahi-daemon 2>/dev/null | grep -c "active"

echo "===LOGS==="
if command -v journalctl >/dev/null; then
    journalctl -p 3 -n 20 --since "30 min ago"
else
    LOG=/var/log/messages
    [ -f /var/log/syslog ] && LOG=/var/log/syslog
    tail -n 50 $LOG | grep -iE "error|fail|critical|segfault|dumped core"
fi
"""

def check_server(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    result = {
        "ip": ip,
        "status": "UNREACHABLE",
        "issues": [],
        "logs": []
    }

    try:
        client.connect(ip, username=user, password=pwd, timeout=10)
        result["status"] = "ONLINE"
        
        stdin, stdout, stderr = client.exec_command(AUDIT_SCRIPT)
        output = stdout.read().decode('utf-8', errors='ignore')
        client.close()

        lines = output.splitlines()
        section = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("==="):
                section = line.strip("=")
                continue
            
            if section == "LIMITS":
                if line.isdigit():
                    val = int(line)
                    if val < 60000:
                        result["issues"].append(f"Low ulimit -n: {val} (Rec: 65535)")
            
            elif section == "SYSCTL":
                if "vm.swappiness" in line:
                    val = int(line.split('=')[-1].strip())
                    if val > 10:
                        result["issues"].append(f"High Swappiness: {val} (Rec: 10)")
                if "fs.file-max" in line:
                    val = int(line.split('=')[-1].strip())
                    if val < 1000000:
                        result["issues"].append(f"Low file-max: {val} (Rec: 1M+)")

            elif section == "RESOURCE":
                if "Swap:" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        total = int(parts[1])
                        used = int(parts[2])
                        if total > 0 and (used/total) > 0.5:
                            result["issues"].append(f"High Swap Usage: {used}MB/{total}MB")

            elif section == "BLOATWARE":
                if line.isdigit():
                    cnt = int(line)
                    if cnt > 0:
                        result["issues"].append(f"Running Desktop/GUI Services ({cnt} detected). Consider slimming.")

            elif section == "LOGS":
                if len(line) > 10:
                    result["logs"].append(line)

        if result["logs"]:
            result["issues"].append(f"Found {len(result['logs'])} recent error logs")

    except Exception as e:
        result["status"] = "ERROR"
        result["issues"].append(str(e))
    
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ips", nargs='+')
    parser.add_argument("--file")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password")
    args = parser.parse_args()

    targets = []
    if args.ips: targets.extend(args.ips)
    if args.file:
        try:
            with open(args.file) as f: targets.extend([l.strip() for l in f if l.strip()])
        except: pass
            
    if not targets:
        print("No targets.")
        sys.exit(1)

    pwd = args.password or getpass.getpass("SSH Password: ")

    print(f"[*] Inspecting {len(targets)} servers...")
    
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_server, ip, args.user, pwd): ip for ip in targets}
        for future in as_completed(futures):
            results.append(future.result())

    print(f"\n{'IP Address':<16} | {'Status':<10} | {'Issues'}")
    print("-" * 60)
    for r in sorted(results, key=lambda x: x['ip']):
        color = GREEN
        if r['issues']: color = RED if r['status'] == "ONLINE" else YELLOW
        issue_str = ", ".join(r['issues'][:2])
        if len(r['issues']) > 2: issue_str += "..."
        if not r['issues']: issue_str = "Clean"
        print(f"{color}{r['ip']:<16}{RESET} | {r['status']:<10} | {issue_str}")

    for r in results:
        if r['issues']:
            print(f"\n{RED}[!] Details for {r['ip']}:{RESET}")
            for i in r['issues']:
                print(f"    - {i}")
            if r['logs']:
                print(f"    {YELLOW}--- Recent Logs ---{RESET}")
                for l in r['logs'][-5:]:
                    print(f"      {l}")

if __name__ == "__main__":
    main()