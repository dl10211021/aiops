import argparse
import paramiko
import threading

def check_xdr(ip, username, password, port=22):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    result = {
        "ip": ip,
        "status": "FAILED",
        "output": ""
    }
    
    cmd = "cd /opt/traps/bin/ && ./cytool runtime query"

    try:
        client.connect(hostname=ip, port=port, username=username, password=password, timeout=10)
        stdin, stdout, stderr = client.exec_command(cmd)
        
        out_str = stdout.read().decode('utf-8', errors='ignore').strip()
        err_str = stderr.read().decode('utf-8', errors='ignore').strip()
        
        if out_str:
            # Try to find version line to keep it compact, otherwise return full
            lines = out_str.splitlines()
            # If multi-line, join with pipe for table
            result["output"] = " | ".join([l.strip() for l in lines if l.strip()])
            result["status"] = "SUCCESS"
        elif err_str:
             result["output"] = f"ERROR: {err_str}"
             result["status"] = "ERR_CMD"
        else:
             result["output"] = "(No output)"
             result["status"] = "EMPTY"
            
        client.close()
    except Exception as e:
        result["output"] = str(e)
        result["status"] = "CONN_ERR"
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Batch XDR Checker")
    parser.add_argument("--ips", nargs='+', required=True, help="List of IP addresses")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    args = parser.parse_args()

    print(f"[*] Checking XDR on {len(args.ips)} servers...")
    print("-" * 120)
    print(f"{'IP Address':<16} | {'Status':<10} | {'XDR Info'}")
    print("-" * 120)

    print_lock = threading.Lock()

    def worker(ip):
        res = check_xdr(ip, args.username, args.password)
        with print_lock:
            # Truncate output if too long for display
            display_info = (res['output'][:90] + '..') if len(res['output']) > 90 else res['output']
            print(f"{res['ip']:<16} | {res['status']:<10} | {display_info}")

    threads = []
    for ip in args.ips:
        t = threading.Thread(target=worker, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
