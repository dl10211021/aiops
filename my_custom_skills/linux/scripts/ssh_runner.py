import argparse
import paramiko
import sys

def run_ssh_command(host, username, password, command, port=22):
    """
    Executes a single command on a remote server via SSH.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"[INFO] Connecting to {username}@{host}:{port}...")
        client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
        
        print(f"[INFO] Executing: {command}")
        stdin, stdout, stderr = client.exec_command(command)
        
        # Read output
        out_str = stdout.read().decode('utf-8', errors='replace')
        err_str = stderr.read().decode('utf-8', errors='replace')
        exit_status = stdout.channel.recv_exit_status()
        
        print("-" * 40)
        if out_str:
            print(out_str.strip())
        if err_str:
            print(f"[STDERR] {err_str.strip()}")
        print("-" * 40)
        
        if exit_status != 0:
            print(f"[WARN] Command finished with exit code {exit_status}")
            sys.exit(exit_status)
            
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Please check credentials.")
        sys.exit(1)
    except paramiko.SSHException as ssh_e:
        print(f"[ERROR] SSH Error: {ssh_e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run commands on remote Linux servers via SSH.")
    parser.add_argument("host", help="Remote hostname or IP")
    parser.add_argument("-u", "--username", required=True, help="SSH Username")
    parser.add_argument("-p", "--password", required=True, help="SSH Password")
    parser.add_argument("-c", "--command", required=True, help="Command to execute")
    parser.add_argument("-P", "--port", type=int, default=22, help="SSH Port")
    
    args = parser.parse_args()
    
    run_ssh_command(args.host, args.username, args.password, args.command, args.port)
