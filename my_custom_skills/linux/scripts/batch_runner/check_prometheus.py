#!/usr/bin/env python3
import paramiko
import argparse
import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_prometheus_agent(ip, user, pwd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    result = {
        "ip": ip,
        "status": "UNKNOWN",
        "service_name": "N/A",
        "version": "N/A",
        "port_9100": False,
        "details": ""
    }

    try:
        client.connect(ip, username=user, password=pwd, timeout=8)
        
        # 1. Check Service Status (node_exporter is the standard name)
        # We check systemctl for common names
        cmd_service = "systemctl is-active node_exporter 2>/dev/null || systemctl is-active prometheus-node-exporter 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(cmd_service)
        status = stdout.read().decode().strip()
        
        if status == "active":
            result["status"] = "RUNNING"
            # Try to guess name
            _, out_name, _ = client.exec_command("systemctl list-units --type=service --state=running | grep exporter | awk '{print $1}' | head -n 1")
            result["service_name"] = out_name.read().decode().strip()
        else:
            result["status"] = "STOPPED/MISSING"

        # 2. Check Port 9100 (Standard node_exporter port)
        # netstat or ss
        cmd_port = "ss -tulpn | grep :9100"
        _, out_port, _ = client.exec_command(cmd_port)
        if ":9100" in out_port.read().decode():
            result["port_9100"] = True
            if result["status"] == "STOPPED/MISSING":
                result["status"] = "RUNNING (Process)" # Detected by port even if service name mismatch

        # 3. Check Version (if running)
        # Try running the binary directly to get version if we can find it, or check process
        cmd_ver = "ps -ef | grep node_exporter | grep -v grep | awk '{print $2}' | xargs -r -I PID ls -l /proc/PID/exe | awk '{print $NF}' | xargs -r -I BIN BIN --version 2>&1 | head -n 1"
        _, out_ver, _ = client.exec_command(cmd_ver)
        ver_str = out_ver.read().decode().strip()
        if ver_str:
            result["version"] = ver_str
        
        client.close()

    except Exception as e:
        result["status"] = "ERROR"
        result["details"] = str(e)
    
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

    print(f"[*] Checking Prometheus Node Exporter on {len(args.ips)} servers...")
    print(f"\n{'IP Address':<16} | {'Status':<15} | {'Port 9100':<10} | {'Version Info'}")
    print("-" * 80)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_prometheus_agent, ip, args.user, pwd): ip for ip in args.ips}
        for future in as_completed(futures):
            r = future.result()
            port_status = "OPEN" if r['port_9100'] else "CLOSED"
            print(f"{r['ip']:<16} | {r['status']:<15} | {port_status:<10} | {r['version']}")

if __name__ == "__main__":
    main()
