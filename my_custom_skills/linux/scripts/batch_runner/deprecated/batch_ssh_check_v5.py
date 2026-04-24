import argparse
import paramiko
import threading

def check_server(ip, username, password, port=22):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    result = {
        "ip": ip,
        "status": "FAILED",
        "info": ""
    }
    
    try:
        client.connect(hostname=ip, port=port, username=username, password=password, timeout=8)
        stdin, stdout, stderr = client.exec_command("uname -r && uptime")
        # Read output and cleanup newlines
        out_str = stdout.read().decode('utf-8', errors='ignore').strip()
        # Explicitly use new variable to avoid syntax errors in string literals in some environments
        separator = " | "
        info = out_str.replace("\n", separator)
        
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

    print(f"[*] Checking {len(args.ips)} servers...")
    print("-" * 80)
    # Using format specifiers for alignment
    header = "{:<16} | {:<8} | {}".format("IP Address", "Status", "System Info")
    print(header)
    print("-" * 80)

    # Lock for printing to avoid scrambled output
    print_lock = threading.Lock()

    def worker(ip):
        res = check_server(ip, args.username, args.password)
        with print_lock:
            # Using format specifiers
            line = "{:<16} | {:<8} | {}".format(res['ip'], res['status'], res['info'])
            print(line)

    for ip in args.ips:
        t = threading.Thread(target=worker, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
