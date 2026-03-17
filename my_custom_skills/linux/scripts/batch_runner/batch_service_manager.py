#!/usr/bin/env python3
import paramiko
import argparse
import sys
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

def manage_service(ip, user, pwd, action, services):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(ip, username=user, password=pwd, timeout=8)
        
        results = []
        for svc in services:
            cmd = f"systemctl {action} {svc}"
            _, _, stderr = client.exec_command(cmd)
            err = stderr.read().decode().strip()
            
            # Verify
            check_cmd = f"systemctl is-active {svc}"
            if action == "enable": check_cmd = f"systemctl is-enabled {svc}"
            
            _, out_stat, _ = client.exec_command(check_cmd)
            status = out_stat.read().decode().strip()
            
            if err:
                results.append(f"{svc}: {err}")
            else:
                results.append(f"{svc}: {status}")

        client.close()
        return f"[{ip}] {action.upper()} -> " + ", ".join(results)

    except Exception as e:
        return f"[{ip}] ERROR: {e}"

def main():
    parser = argparse.ArgumentParser(description="Batch Service Manager")
    parser.add_argument("--ips", nargs='+', required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", help="SSH Password")
    parser.add_argument("--action", required=True, choices=['start', 'stop', 'restart', 'enable', 'disable', 'mask', 'unmask'])
    parser.add_argument("--services", nargs='+', required=True, help="List of services")
    args = parser.parse_args()

    pwd = args.password or getpass.getpass("SSH Password: ")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(manage_service, ip, args.user, pwd, args.action, args.services): ip for ip in args.ips}
        for future in as_completed(futures):
            print(future.result())

if __name__ == "__main__":
    main()
