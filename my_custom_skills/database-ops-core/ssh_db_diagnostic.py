import paramiko
import sys
import os

# 目标资产信息
HOST = "172.17.8.151"
PORT = 22
USERNAME = "root"
PASSWORD = "OpsCore_Auto_Injected_Pass" # 模拟密码，实际需从上下文获取，这里仅为脚本结构

def get_mysql_config():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 注意：在实际环境中，密码应从环境变量或安全存储中获取。
        # 这里我们假设密码已知或脚本在受控环境中运行。
        # 由于无法直接获取密码，我们尝试使用无密码连接或报错提示用户。
        print("Attempting to connect to %s..." % HOST)
        
        # 尝试连接，如果密码错误，paramiko 会抛出异常
        client.connect(hostname=HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=10)
        
        # 执行命令获取 MySQL 配置
        # 我们只抓取关键配置，避免输出过多无用信息
        commands = [
            "mysql -u root -e 'SHOW VARIABLES;' 2>/dev/null",
            "mysql -u root -e 'SHOW GLOBAL STATUS;' 2>/dev/null",
            "cat /etc/my.cnf 2>/dev/null || cat /etc/mysql/my.cnf 2>/dev/null || echo 'Config file not found in default locations'"
        ]
        
        for cmd in commands:
            print(f"--- Executing: {cmd} ---")
            stdin, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            if output:
                print(output)
            if error:
                print(f"STDERR: {error}")
                
        client.close()
        print("Connection closed.")
        
    except paramiko.AuthenticationException:
        print("ERROR: Authentication failed. Please check credentials.")
        return False
    except paramiko.SSHException as e:
        print(f"ERROR: SSH exception: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False
    return True

if __name__ == "__main__":
    get_mysql_config()