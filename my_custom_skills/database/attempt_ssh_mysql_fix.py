
import paramiko
import sys

def attempt_ssh_mysql_fix(host, password, new_db_pass):
    print(f"Attempting SSH connection to {host} with root/{password}...")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username='root', password=password, timeout=10)
        
        print("SSH connection successful!")
        
        # Method 1: Try direct mysql command (often works for local root via socket)
        print("Method 1: Trying 'mysql -u root'...")
        stdin, stdout, stderr = client.exec_command(f"mysql -u root -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '{new_db_pass}'; FLUSH PRIVILEGES;\"")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("Successfully changed MySQL root password via local socket!")
            return True
        else:
            err = stderr.read().decode()
            print(f"Method 1 failed: {err}")
            
            # Method 2: Skip Grant Tables (Heavy duty)
            print("Method 2: Attempting --skip-grant-tables reset...")
            
            # Detect service name (mysqld or mysql or mariadb)
            check_svc_cmd = "systemctl list-unit-files | grep -E 'mysql|mariadb' | head -n 1 | awk '{print $1}'"
            stdin, stdout, stderr = client.exec_command(check_svc_cmd)
            service_name = stdout.read().decode().strip()
            
            if not service_name:
                print("Could not detect MySQL service name.")
                return False
                
            print(f"Detected service: {service_name}")
            
            cmds = [
                f"systemctl stop {service_name}",
                "mysqld_safe --skip-grant-tables --skip-networking &",
                "sleep 5",
                f"mysql -u root -e \"FLUSH PRIVILEGES; ALTER USER 'root'@'localhost' IDENTIFIED BY '{new_db_pass}';\"",
                "pkill mysqld",
                f"systemctl start {service_name}"
            ]
            
            for cmd in cmds:
                print(f"Executing: {cmd}")
                stdin, stdout, stderr = client.exec_command(cmd)
                status = stdout.channel.recv_exit_status()
                if status != 0:
                    print(f"Command failed: {stderr.read().decode()}")
                    # Continue anyway as pkill might fail if process already dead
            
            print("Password reset sequence completed. Please verify.")
            return True

    except Exception as e:
        print(f"SSH connection failed or error occurred: {str(e)}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python script.py <HOST> <SSH_PASS> <NEW_DB_PASS>")
        sys.exit(1)
        
    host = sys.argv[1]
    ssh_pass = sys.argv[2]
    new_db_pass = sys.argv[3]
    
    attempt_ssh_mysql_fix(host, ssh_pass, new_db_pass)
