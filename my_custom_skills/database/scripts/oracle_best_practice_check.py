import argparse
import paramiko
import oracledb
import json

def check_os(host, user, password):
    results = {}
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password)
        
        def run(cmd):
            _, stdout, _ = ssh.exec_command(cmd)
            return stdout.read().decode().strip()

        # 1. Swappiness
        try:
            val = int(run("sysctl -n vm.swappiness"))
            results['swappiness'] = val
        except: results['swappiness'] = -1
        
        # 2. THP
        thp = run("cat /sys/kernel/mm/transparent_hugepage/enabled")
        results['thp'] = "never" in thp and "[never]" in thp
        
        # 3. HugePages
        try:
            val = int(run("grep HugePages_Total /proc/meminfo | awk '{print $2}'"))
            results['hugepages_total'] = val
        except: results['hugepages_total'] = -1
        
        # 4. Kernel Params
        try:
            results['file_max'] = int(run("sysctl -n fs.file-max"))
        except: results['file_max'] = -1
            
        ssh.close()
    except Exception as e:
        results['error'] = str(e)
    return results

def check_db(host, user, password, sid):
    results = {}
    dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT=1521))(CONNECT_DATA=(SID={sid})))"
    try:
        conn = oracledb.connect(user=user, password=password, dsn=dsn, mode=oracledb.SYSDBA)
        cursor = conn.cursor()
        
        def get_param(name):
            cursor.execute(f"SELECT value FROM v$parameter WHERE name='{name}'")
            row = cursor.fetchone()
            return row[0] if row else None

        results['memory_target'] = get_param('memory_target')
        results['processes'] = int(get_param('processes'))
        
        # Redo Log Size
        cursor.execute("SELECT min(bytes)/1024/1024 FROM v$log")
        row = cursor.fetchone()
        results['min_log_size_mb'] = row[0] if row else 0
        
        conn.close()
    except Exception as e:
        results['error'] = str(e)
    return results

def evaluate(os_data, db_data):
    issues = []
    
    # --- OS Eval ---
    if os_data and not os_data.get('error'):
        if os_data['swappiness'] > 10:
            issues.append(f"[OS] vm.swappiness is {os_data['swappiness']} (Recommended: <= 10)")
        
        if not os_data['thp']:
            issues.append("[OS] Transparent Huge Pages (THP) NOT disabled (Recommended: [never])")
            
        if os_data['hugepages_total'] == 0:
            if db_data and db_data.get('memory_target') and int(db_data['memory_target']) > 0:
                 pass 
            else:
                 issues.append("[OS] HugePages not configured (Recommended for ASMM/SGA > 8GB)")
        
        if os_data['file_max'] < 6815744:
            issues.append(f"[OS] fs.file-max ({os_data['file_max']}) < 6.8M")
            
    elif os_data.get('error'):
        issues.append(f"[OS] Check Failed: {os_data['error']}")
            
    # --- DB Eval ---
    if db_data and not db_data.get('error'):
        # Memory
        mem_target = int(db_data['memory_target']) if db_data['memory_target'] else 0
        if mem_target > 0:
             issues.append("[DB] MEMORY_TARGET is set (AMM). Best practice for Linux often prefers ASMM.")
        
        if db_data['processes'] < 300:
            issues.append(f"[DB] PROCESSES ({db_data['processes']}) might be too low.")
            
        if db_data['min_log_size_mb'] < 512:
            issues.append(f"[DB] Redo Log Size ({db_data['min_log_size_mb']} MB) is small (Recommended: >= 512MB).")

    elif db_data.get('error'):
        issues.append(f"[DB] Check Failed: {db_data['error']}")

    return issues

def main():
    parser = argparse.ArgumentParser(description="Oracle Best Practices Auditor")
    parser.add_argument("--host", required=True)
    parser.add_argument("--os-user", default="root")
    parser.add_argument("--os-pass", required=True)
    parser.add_argument("--db-user", default="sys")
    parser.add_argument("--db-pass", required=True)
    parser.add_argument("--sid", default="orcl")
    
    args = parser.parse_args()
    
    os_res = check_os(args.host, args.os_user, args.os_pass)
    db_res = check_db(args.host, args.db_user, args.db_pass, args.sid)
    
    issues = evaluate(os_res, db_res)
    
    if not issues:
        print(json.dumps({"status": "PASS", "host": args.host, "issues": []}, indent=2))
    else:
        print(json.dumps({"status": "WARNING", "host": args.host, "issues": issues}, indent=2))

if __name__ == '__main__':
    main()
