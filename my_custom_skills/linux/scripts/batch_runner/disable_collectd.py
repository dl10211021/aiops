#!/usr/bin/env python3
import paramiko
import argparse
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

def disable_collectd(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    result = {
        "ip": ip,
        "status": "UNKNOWN",
        "output": ""
    }

    try:
        client.connect(ip, username=user, password=pwd, timeout=8)
        
        # Stop and Disable collectd
        cmd = "systemctl stop collectd && systemctl disable collectd"
        stdin, stdout, stderr = client.exec_command(cmd)
        
        out_str = stdout.read().decode().strip()
        err_str = stderr.read().decode().strip()
        
        # Verify status
        check_cmd = "systemctl is-active collectd"
        _, out_status, _ = client.exec_command(check_cmd)
        final_status = out_status.read().decode().strip()
        
        if final_status != "active":
             result["status"] = "SUCCESS (Stopped)"
        else:
             result["status"] = "FAILED (Still Active)"
             result["output"] = err_str

        client.close()

    except Exception as e:
        result["status"] = "ERROR"
        result["output"] = str(e)
    
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

    print(f"[*] Disabling 'collectd' on {len(args.ips)} servers...")
    print(f"\n{'IP Address':<16} | {'Status':<25} | {'Details'}")
    print("-" * 80)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(disable_collectd, ip, args.user, pwd): ip for ip in args.ips}
        for future in as_completed(futures):
            r = future.result()
            print(f"{r['ip']:<16} | {r['status']:<25} | {r['output']}")

if __name__ == "__main__":
    main()
