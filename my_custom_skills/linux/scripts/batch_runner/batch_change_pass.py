import argparse
import paramiko
import threading
import time

def change_password(ip, username, old_password, new_password, port=22):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    result = {
        "ip": ip,
        "status": "FAILED",
        "msg": ""
    }
    
    # Step 1: Connect with OLD password
    try:
        client.connect(hostname=ip, port=port, username=username, password=old_password, timeout=10)
    except Exception as e:
        result["msg"] = f"Login failed (Old Pass): {str(e)}"
        return result

    # Step 2: Change password using chpasswd
    try:
        # Note: Single quotes around the string to protect special chars in shell
        cmd = f"echo '{username}:{new_password}' | chpasswd"
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            err = stderr.read().decode().strip()
            result["msg"] = f"Change Command Failed: {err}"
            client.close()
            return result
            
        client.close()
    except Exception as e:
        result["msg"] = f"Exec Failed: {str(e)}"
        if client: client.close()
        return result

    # Step 3: Verify by connecting with NEW password
    # Give it a brief moment, though usually instant
    time.sleep(1)
    try:
        client.connect(hostname=ip, port=port, username=username, password=new_password, timeout=10)
        result["status"] = "SUCCESS"
        result["msg"] = "Changed & Verified"
        client.close()
    except Exception as e:
        result["msg"] = f"Verification Login Failed: {str(e)}"
        result["status"] = "PARTIAL_FAIL" # Password might have changed but can't login, or didn't change.

    return result

def main():
    parser = argparse.ArgumentParser(description="Batch Password Changer")
    parser.add_argument("--ips", nargs='+', required=True, help="List of IP addresses")
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("--oldpass", required=True)
    parser.add_argument("--newpass", required=True)
    args = parser.parse_args()

    print(f"[*] Changing password for user '{args.username}' on {len(args.ips)} servers...")
    print(f"[*] New Password: {args.newpass}")
    print("-" * 80)
    print(f"{'IP Address':<16} | {'Status':<12} | {'Message'}")
    print("-" * 80)

    print_lock = threading.Lock()

    def worker(ip):
        res = change_password(ip, args.username, args.oldpass, args.newpass)
        with print_lock:
            print(f"{res['ip']:<16} | {res['status']:<12} | {res['msg']}")

    threads = []
    for ip in args.ips:
        t = threading.Thread(target=worker, args=(ip,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
