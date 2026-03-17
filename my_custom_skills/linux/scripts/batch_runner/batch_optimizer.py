#!/usr/bin/env python3
import paramiko
import argparse
import sys
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

SYSCTL_CONF = """
vm.swappiness = 10
fs.file-max = 2000000
net.core.somaxconn = 4096
net.ipv4.ip_local_port_range = 10000 65000
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_tw_reuse = 1
"""

LIMITS_CONF = """
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
"""

# Services to kill/mask in SLIM mode
SLIM_SERVICES = [
    "gdm", "gnome-shell", "packagekit", "upower", "colord", 
    "cups", "avahi-daemon", "ModemManager", 
    "tracker-store", "tracker-miner-fs", "tracker-extract"
]

def exec_wait(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status() # Wait for command to finish
    return exit_status

def optimize_server(ip, user, pwd, mask_services=None, do_slim=False):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    log = []
    try:
        client.connect(ip, username=user, password=pwd, timeout=10)
        
        # 0. Slimming Mode
        if do_slim:
            log.append("--- Slimming ---")
            # Mask services
            for svc in SLIM_SERVICES:
                # Try stop first
                exec_wait(client, f"systemctl stop {svc}")
                # Then mask
                exec_wait(client, f"systemctl mask {svc}")
            
            # Set default target
            exec_wait(client, "systemctl set-default multi-user.target")
            
            # Force kill lingering processes
            exec_wait(client, "pkill -f gnome; pkill -f packagekit; pkill -f tracker")
            
            log.append("Disabled Desktop/GUI services & set multi-user target")

        # 1. Custom Mask
        if mask_services:
            for svc in mask_services:
                exec_wait(client, f"systemctl mask --now {svc}")
                log.append(f"Masked {svc}")

        # 2. Sysctl
        cmd_sys = f"echo '{SYSCTL_CONF.strip()}' > /etc/sysctl.d/99-gemini-opt.conf && sysctl -p /etc/sysctl.d/99-gemini-opt.conf"
        exec_wait(client, cmd_sys)
        log.append("Applied Sysctl")

        # 3. Limits
        cmd_lim = f"echo '{LIMITS_CONF.strip()}' > /etc/security/limits.d/99-gemini-limits.conf"
        exec_wait(client, cmd_lim)
        log.append("Applied Limits")

        client.close()
        return f"[{ip}] SUCCESS: " + ", ".join(log)

    except Exception as e:
        return f"[{ip}] ERROR: {e}"

def main():
    parser = argparse.ArgumentParser(description="Batch System Optimizer")
    parser.add_argument("--ips", nargs='+')
    parser.add_argument("--file")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password")
    parser.add_argument("--mask", nargs='+', help="Specific services to mask")
    parser.add_argument("--slim", action="store_true", help="Enable 'Deep Slim' mode (Disable GUI/Desktop/Tracker)")
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
    
    print(f"[*] Optimizing {len(targets)} servers (Slim Mode: {args.slim})...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(optimize_server, ip, args.user, pwd, args.mask, args.slim): ip for ip in targets}
        for future in as_completed(futures):
            print(future.result())

if __name__ == "__main__":
    main()