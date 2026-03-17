import argparse
import paramiko
import threading
import socket

def check_server(ip, username, password, port=22):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    result = {
        "ip": ip,
        "status": "FAILED",
        "info": ""
    }
    
    try:
        client.connect(hostname=ip, port=port, username=username, password=password, timeout=5)
        stdin, stdout, stderr = client.exec_command("uname -r && uptime -p")
        info = stdout.read().decode('utf-8').strip().replace('\n', ' | ')
        result["status"] = "SUCCESS"
        result["info"] = info
        client.close()
    except Exception as e:
        result["info"] = str(e)
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Batch SSH Login Checker")
    parser.add_argument("--ips", nargs='+', required=True, help="List of IP addresses")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    args = parser.parse_args()

    threads = []
    results = []

    print(f"[*] Checking {len(args.ips)} servers...")
    print("-" * 60)
    print(f"{'IP Address':<18} | {'Status':<10} | {'Info'}")
    print("-" * 60)

    # Simple threaded execution
    def worker(ip):
        res = check_server(ip, args.username, args.password)
        print(f"{res['ip']:<18} | {res['status']:<10} | {res['info']}")
        results.append(res)

    for ip in args.ips:
        t = threading.Thread(target=worker, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
