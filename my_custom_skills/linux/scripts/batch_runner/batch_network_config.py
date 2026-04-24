#!/usr/bin/env python3
import paramiko
import argparse
import getpass
import re
import sys
import logging
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# --- Logging Setup ---
log_filename = f"network_change_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

# --- Lock for thread-safe logging/printing ---
print_lock = threading.Lock()

def safe_print(msg):
    with print_lock:
        print(msg)

def get_ssh_client(ip, user, pwd, timeout=10):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=pwd, timeout=timeout)
        return client
    except Exception as e:
        logger.error(f"[{ip}] Connection failed: {e}")
        return None

def exec_command(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    return out, err

def configure_server(ip, user, pwd, dns_server, gateway_override=None, dry_run=False):
    logger.info(f"[{ip}] Starting configuration...")
    client = get_ssh_client(ip, user, pwd)
    if not client:
        return False

    try:
        # 1. Detect OS
        os_release, _ = exec_command(client, "cat /etc/os-release")
        if "CentOS" not in os_release and "Red Hat" not in os_release:
            logger.warning(f"[{ip}] Skipping non-RHEL/CentOS system.")
            return False

        # 2. Get Route Info (Interface & Gateway)
        route_info, _ = exec_command(client, "ip route get 8.8.8.8")
        match_dev = re.search(r'dev\s+(\S+)', route_info)
        match_gw = re.search(r'via\s+(\S+)', route_info)

        if not match_dev:
            logger.error(f"[{ip}] Could not determine active interface.")
            return False

        interface = match_dev.group(1)
        # Use detected gateway or override
        current_gateway = match_gw.group(1) if match_gw else None
        gateway = gateway_override if gateway_override else current_gateway

        # 3. Get IP Details
        ip_info, _ = exec_command(client, f"ip -o -4 addr show dev {interface}")
        ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', ip_info)
        
        if not ip_match:
            logger.error(f"[{ip}] Could not determine current IP info.")
            return False

        current_ip = ip_match.group(1)
        prefix = ip_match.group(2)
        
        logger.info(f"[{ip}] Detected: IF={interface}, IP={current_ip}/{prefix}, GW={gateway}")

        # 4. Prepare Config
        cfg_path = f"/etc/sysconfig/network-scripts/ifcfg-{interface}"
        
        # Check if file exists
        check_file, _ = exec_command(client, f"ls {cfg_path}")
        if "No such file" in check_file:
            logger.error(f"[{ip}] Config file {cfg_path} not found.")
            return False

        # Read current to preserve UUID
        current_cfg, _ = exec_command(client, f"cat {cfg_path}")
        uuid = re.search(r'UUID=.*', current_cfg)
        
        new_lines = [
            "TYPE=Ethernet",
            "PROXY_METHOD=none",
            "BROWSER_ONLY=no",
            uuid.group(0) if uuid else "",
            "BOOTPROTO=static",
            "DEFROUTE=yes",
            "IPV4_FAILURE_FATAL=no",
            f"NAME={interface}",
            f"DEVICE={interface}",
            "ONBOOT=yes",
            f"IPADDR={current_ip}",
            f"PREFIX={prefix}",
            f"DNS1={dns_server}"
        ]
        
        if gateway:
            new_lines.append(f"GATEWAY={gateway}")
            
        new_content = "\n".join(filter(None, new_lines))

        if dry_run:
            logger.info(f"[{ip}] [DRY-RUN] Would write to {cfg_path}:\n{new_content}")
            return True

        # 5. Backup & Write
        exec_command(client, f"cp {cfg_path} {cfg_path}.bak_{datetime.now().strftime('%H%M%S')}")
        
        # Write via echo (handling root perms)
        cmd_write = f"echo '{new_content}' > {cfg_path}"
        exec_command(client, cmd_write)
        
        # 6. Restart Network (nmcli priority)
        logger.info(f"[{ip}] Restarting network...")
        restart_cmd = f"nmcli c reload && nmcli c up {interface}"
        
        # Execute restart (this might hang if connection drops, but usually safe for static->static)
        stdout, stderr = exec_command(client, restart_cmd)
        
        if stderr and "command not found" in stderr:
            # Fallback for old CentOS 7 minimal
            logger.info(f"[{ip}] nmcli not found, trying systemctl...")
            stdout, stderr = exec_command(client, "systemctl restart network")
        
        if stderr and "Connection refused" not in stderr:
             logger.warning(f"[{ip}] Restart stderr: {stderr}")

        logger.info(f"[{ip}] Configuration complete.")
        return True

    except Exception as e:
        logger.error(f"[{ip}] Unexpected error: {e}")
        return False
    finally:
        client.close()

def main():
    parser = argparse.ArgumentParser(description="Batch Network Configurator (RHEL/CentOS)")
    parser.add_argument("--hosts", help="Comma separated list of IPs (e.g., 192.168.1.10,192.168.1.11)")
    parser.add_argument("--file", help="Path to file containing IPs (one per line)")
    parser.add_argument("--user", default="root", help="SSH Username")
    parser.add_argument("--password", help="SSH Password (WARNING: Unsafe in history)")
    parser.add_argument("--dns", required=True, help="DNS Server IP")
    parser.add_argument("--gateway", help="Override Gateway IP (Optional, defaults to auto-detect)")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent threads")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without writing")
    
    args = parser.parse_args()

    # IP Source Logic
    target_ips = []
    if args.hosts:
        target_ips = [ip.strip() for ip in args.hosts.split(',')]
    elif args.file:
        if os.path.exists(args.file):
            with open(args.file, 'r') as f:
                target_ips = [line.strip() for line in f if line.strip()]
        else:
            print(f"File {args.file} not found.")
            sys.exit(1)
    else:
        print("Error: Must provide --hosts or --file")
        sys.exit(1)

    # Password Logic
    password = args.password
    if not password:
        password = os.environ.get("SSH_PASSWORD")
    if not password:
        password = getpass.getpass("SSH Password: ")

    logger.info(f"Starting batch configuration on {len(target_ips)} hosts...")
    
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(configure_server, ip, args.user, password, args.dns, args.gateway, args.dry_run): ip 
            for ip in target_ips
        }
        
        for future in as_completed(futures):
            ip = futures[future]
            try:
                success = future.result()
                status = "SUCCESS" if success else "FAILED"
                print(f"Finished {ip}: {status}")
            except Exception as e:
                logger.error(f"[{ip}] Thread exception: {e}")

    logger.info("Batch processing finished. Check log file for details.")

if __name__ == "__main__":
    main()
