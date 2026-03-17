import argparse
import paramiko
import threading
import sys

def check_server_health(ip, username, password, port=22):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    result = {
        "ip": ip,
        "status": "FAILED",
        "hostname": "N/A",
        "load": "N/A",
        "mem": "N/A",
        "disk": "N/A"
    }
    
    # Corrected command string:
    # Use triple quotes for Python string to handle internal quotes easier
    # Use simple awk without complex printf formatting to avoid Python string interpolation issues
    
    cmd = """export LANG=C; hostname; uptime | awk -F'load average:' '{ print $2 }' | xargs; free -m | awk '/Mem:/ { print $3 " / " $2 " MB" }'; df -h / | awk 'NR==2 { print $5 }'"""

    try:
        client.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
        stdin, stdout, stderr = client.exec_command(cmd)
        
        output = stdout.read().decode('utf-8', errors='ignore').strip().splitlines()
        output = [line.strip() for line in output if line.strip()]
        
        if len(output) >= 4:
            result["status"] = "OK"
            result["hostname"] = output[0]
            result["load"] = output[1]
            result["mem"] = output[2]
            result["disk"] = output[3]
        else:
            result["status"] = "PARTIAL"
            if len(output) > 0: result["hostname"] = output[0]
            
        client.close()
    except Exception as e:
        result["status"] = "ERR"
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Batch Server Health Inspector")
    parser.add_argument("--ips", nargs='+', required=True, help="List of IP addresses")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    args = parser.parse_args()

    print(f"[*] Inspecting {len(args.ips)} servers...")
    print(f"{'IP Address':<16} | {'Hostname':<20} | {'Status':<6} | {'Disk':<6} | {'Memory Use':<18} | {'Load Average'}")
    print("-" * 95)

    print_lock = threading.Lock()

    def worker(ip):
        res = check_server_health(ip, args.username, args.password)
        with print_lock:
            print(f"{res['ip']:<16} | {res['hostname']:<20} | {res['status']:<6} | {res['disk']:<6} | {res['mem']:<18} | {res['load']}")

    threads = []
    for ip in args.ips:
        t = threading.Thread(target=worker, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
