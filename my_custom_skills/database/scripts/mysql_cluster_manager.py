import argparse
import paramiko
import time
import sys

class MySQLClusterManager:
    def __init__(self, master_ip, slave_ip, ssh_user, ssh_pass, db_root_pass, repl_user, repl_pass):
        self.master = {'ip': master_ip, 'role': 'Master'}
        self.slave = {'ip': slave_ip, 'role': 'Slave'}
        self.nodes = [self.master, self.slave]
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass
        self.db_root_pass = db_root_pass
        self.repl_user = repl_user
        self.repl_pass = repl_pass

    def _get_ssh_client(self, ip):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(hostname=ip, username=self.ssh_user, password=self.ssh_pass, timeout=10)
            return client
        except Exception as e:
            print(f"[ERROR] Connection to {ip} failed: {e}")
            sys.exit(1)

    def _exec(self, client, cmd, ignore_error=False):
        print(f"[{client.get_transport().getpeername()[0]}] Exec: {cmd[:50]}...")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0 and not ignore_error:
            print(f"[ERROR] Command failed: {cmd}")
            print(f"[STDERR] {err}")
            if not ignore_error:
                sys.exit(1)
        return out

    def _write_file(self, client, path, content):
        """Writes content to a remote file using sftp to avoid shell escaping issues."""
        sftp = client.open_sftp()
        with sftp.file(path, 'w') as f:
            f.write(content)
        sftp.close()
        print(f"[{client.get_transport().getpeername()[0]}] Wrote file: {path}")

    def _run_mysql(self, client, sql):
        # Escape double quotes in SQL
        sql_escaped = sql.replace('"', '\\"')
        cmd = f"mysql -u root -p'{self.db_root_pass}' -N -s -e \"{sql_escaped}\""
        return self._exec(client, cmd)

    def deploy(self):
        print(f"[*] Deploying MySQL Cluster (Master: {self.master['ip']}, Slave: {self.slave['ip']})")
        
        for node in self.nodes:
            ip = node['ip']
            client = self._get_ssh_client(ip)
            
            # 1. Setup Mirrors
            self._exec(client, "rm -f /etc/yum.repos.d/mysql-community.repo /etc/yum.repos.d/aliyun-mysql.repo", ignore_error=True)
            aliyun_repo = """[baseos]
name=CentOS-8 - BaseOS - mirrors.aliyun.com
baseurl=https://mirrors.aliyun.com/centos-vault/8.5.2111/BaseOS/$basearch/os/
gpgcheck=0
enabled=1

[appstream]
name=CentOS-8 - AppStream - mirrors.aliyun.com
baseurl=https://mirrors.aliyun.com/centos-vault/8.5.2111/AppStream/$basearch/os/
gpgcheck=0
enabled=1
"""
            self._write_file(client, "/etc/yum.repos.d/aliyun-base.repo", aliyun_repo)
            self._exec(client, "mkdir -p /etc/yum.repos.d/bak && mv /etc/yum.repos.d/redhat.repo /etc/yum.repos.d/bak/", ignore_error=True)
            self._exec(client, "dnf clean all", ignore_error=True)
            self._exec(client, "dnf makecache", ignore_error=True)
            
            # 2. Install MySQL
            if not self._exec(client, "rpm -qa | grep mysql-server", ignore_error=True):
                self._exec(client, "dnf module disable -y mysql", ignore_error=True)
                self._exec(client, "dnf module enable -y mysql:8.0", ignore_error=True)
                self._exec(client, "dnf install -y mysql-server")
                self._exec(client, "systemctl enable --now mysqld")
                time.sleep(10)
                # Init Root Pass
                self._exec(client, f"mysqladmin -u root password '{self.db_root_pass}'", ignore_error=True)
            
            # 3. Firewall
            self._exec(client, "firewall-cmd --permanent --add-service=mysql", ignore_error=True)
            self._exec(client, "firewall-cmd --reload", ignore_error=True)
            self._exec(client, "setenforce 0", ignore_error=True)
            self._exec(client, "sed -i 's/^SELINUX=.*/SELINUX=permissive/g' /etc/selinux/config", ignore_error=True)
            
            client.close()

        # 4. Configure Nodes
        self._configure_node(self.master, 1)
        self._configure_node(self.slave, 2)
        
        # 5. Setup Replication
        self._setup_replication()

    def _configure_node(self, node, server_id):
        ip = node['ip']
        is_master = (node['role'] == 'Master')
        client = self._get_ssh_client(ip)
        
        config = f"""[mysqld]
server-id={server_id}
datadir=/var/lib/mysql
socket=/var/lib/mysql/mysql.sock
log-error=/var/log/mysql/mysqld.log
pid-file=/var/run/mysqld/mysqld.pid
gtid_mode=ON
enforce_gtid_consistency=ON
binlog_expire_logs_seconds=2592000
max_connections=1000
default_authentication_plugin=mysql_native_password
innodb_buffer_pool_size=4G
skip-name-resolve
"""
        if is_master:
            config += "log-bin=mysql-bin\nbinlog_format=ROW\n"
        else:
            config += "relay-log=mysql-relay-bin\nread_only=1\nsuper_read_only=1\n"

        self._write_file(client, "/etc/my.cnf", config)
        self._exec(client, "systemctl restart mysqld")
        time.sleep(10)
        client.close()

    def _setup_replication(self):
        print("[*] Setting up Replication...")
        
        # Master: Create Repl User
        m_client = self._get_ssh_client(self.master['ip'])
        sql = f"CREATE USER IF NOT EXISTS '{self.repl_user}'@'%' IDENTIFIED WITH mysql_native_password BY '{self.repl_pass}'; GRANT REPLICATION SLAVE ON *.* TO '{self.repl_user}'@'%'; FLUSH PRIVILEGES;"
        self._run_mysql(m_client, sql)
        
        # Master: Allow Remote Root (Optional)
        sql = f"CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED WITH mysql_native_password BY '{self.db_root_pass}'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;"
        self._run_mysql(m_client, sql)
        m_client.close()

        # Slave: Start Replication
        s_client = self._get_ssh_client(self.slave['ip'])
        sql = f"STOP SLAVE; CHANGE MASTER TO MASTER_HOST='{self.master['ip']}', MASTER_USER='{self.repl_user}', MASTER_PASSWORD='{self.repl_pass}', MASTER_AUTO_POSITION=1, GET_MASTER_PUBLIC_KEY=1; START SLAVE;"
        self._run_mysql(s_client, sql)
        
        # Verify
        time.sleep(5)

        status = self._run_mysql(s_client, r"SHOW SLAVE STATUS\G")
        if "Slave_IO_Running: Yes" in status and "Slave_SQL_Running: Yes" in status:
            print("[SUCCESS] Replication is running.")
        else:
            print("[WARNING] Replication might have issues.")
            print(status)
        s_client.close()

    def check(self):
        print("[*] Checking Cluster Health...")
        for node in self.nodes:
            ip = node['ip']
            role = node['role']
            client = self._get_ssh_client(ip)
            print(f"\n--- {role}: {ip} ---")
            
            try:
                # Check Variables
                vars_check = "server_id,read_only,super_read_only,gtid_mode,innodb_buffer_pool_size"
                # Safe way to query multiple vars
                sql = f"SHOW GLOBAL VARIABLES WHERE Variable_name IN ({','.join([repr(x) for x in vars_check.split(',')])})"
                res = self._run_mysql(client, sql)
                print(res)

                if role == 'Slave':
                    print("\n[Replication Status]")
                    status = self._run_mysql(client, r"SHOW SLAVE STATUS\G")
                    for line in status.split('\n'):
                        if any(k in line for k in ['Slave_IO_Running', 'Slave_SQL_Running', 'Seconds_Behind_Master', 'Last_IO_Error']):
                            print(line.strip())
            except Exception as e:
                print(f"Check failed: {e}")
            
            client.close()

def main():
    parser = argparse.ArgumentParser(description="MySQL Cluster Manager")
    parser.add_argument("command", choices=['deploy', 'check'], help="Command to execute")
    
    parser.add_argument("--master", required=True, help="Master IP")
    parser.add_argument("--slave", required=True, help="Slave IP")
    parser.add_argument("--ssh-user", default="root")
    parser.add_argument("--ssh-pass", required=True)
    parser.add_argument("--db-root-pass", default="StrongPass123!@#")
    parser.add_argument("--repl-user", default="repl_user")
    parser.add_argument("--repl-pass", default="ReplPass123!@#")

    args = parser.parse_args()

    mgr = MySQLClusterManager(
        args.master, args.slave, 
        args.ssh_user, args.ssh_pass, 
        args.db_root_pass, args.repl_user, args.repl_pass
    )

    if args.command == 'deploy':
        mgr.deploy()
    elif args.command == 'check':
        mgr.check()

if __name__ == "__main__":
    main()

