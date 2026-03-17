#!/usr/bin/env python3
import paramiko
import argparse
import threading
import sys
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration Content ---

# 1. /etc/sysctl.d/99-optimization.conf
SYSCTL_CONTENT = """
# System Optimization
vm.swappiness = 10
fs.file-max = 2000000
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 10000 65000
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_tw_reuse = 1
"""

# 2. /etc/security/limits.d/99-limits.conf
LIMITS_CONTENT = """
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
"""

# 3. Services to Mask (Disable completely)
SERVICES_TO_MASK = [
    "tracker-store",
    "tracker-miner-fs",
    "tracker-extract",
    "tracker-miner-apps",
    "tracker-writeback"
]

def apply_optimization(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    log = []
    
    try:
        client.connect(ip, username=user, password=pwd, timeout=10)
        
        # A. Stop & Mask Tracker Services (Fix Core Dumps)
        log.append("--- Cleaning Tracker ---")
        for svc in SERVICES_TO_MASK:
            # We use --now to stop immediately
            cmd = f"systemctl mask --now {svc}" 
            _, _, stderr = client.exec_command(cmd)
            err = stderr.read().decode().strip()
            if err:
                log.append(f"Warn masking {svc}: {err}")
            else:
                log.append(f"Masked {svc}")
        
        # Kill any lingering processes just in case
        client.exec_command("pkill -9 -f tracker")

        # B. Apply Sysctl
        log.append("--- Applying Sysctl ---")
        cmd_sysctl = f"echo '{SYSCTL_CONTENT.strip()}' > /etc/sysctl.d/99-optimization.conf && sysctl -p /etc/sysctl.d/99-optimization.conf"
        _, stdout, stderr = client.exec_command(cmd_sysctl)
        if stderr.read():
             log.append("Sysctl applied with some stderr output (check if critical)")
        else:
             log.append("Sysctl parameters applied.")

        # C. Apply Limits
        log.append("--- Applying Limits ---")
        cmd_limits = f"echo '{LIMITS_CONTENT.strip()}' > /etc/security/limits.d/99-limits.conf"
        client.exec_command(cmd_limits)
        log.append("Limits config written (requires re-login to take effect for sessions).")

        client.close()
        return f"[{ip}] SUCCESS\n" + "\n".join(f"  {l}" for l in log)

    except Exception as e:
        return f"[{ip}] ERROR: {str(e)}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ips", nargs='+', required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=False)
    args = parser.parse_args()

    pwd = args.password
    if not pwd:
        pwd = getpass.getpass("SSH Password: ")

    print(f"[*] Applying Fixes & Optimizations to {len(args.ips)} servers...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(apply_optimization, ip, args.user, pwd): ip for ip in args.ips}
        for future in as_completed(futures):
            print(future.result())

if __name__ == "__main__":
    main()
