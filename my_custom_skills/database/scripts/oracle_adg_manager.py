import argparse
import oracledb
import time
import sys
import json

def get_connection(args, host, sid):
    dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={args.port}))(CONNECT_DATA=(SID={sid})))"
    try:
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn, mode=oracledb.SYSDBA)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Connection failed to {host}: {str(e)}"}))
        return None

def check_adg_status(args):
    report = {}
    
    # Check Primary
    conn_p = get_connection(args, args.primary_host, args.sid)
    if conn_p:
        cursor = conn_p.cursor()
        cursor.execute("SELECT database_role, open_mode, switchover_status, protection_mode FROM v$database")
        row = cursor.fetchone()
        report['primary'] = {
            'role': row[0], 'mode': row[1], 'switchover': row[2], 'protection': row[3]
        }
        
        # Check Transport
        cursor.execute("SELECT dest_id, status, error, destination FROM v$archive_dest WHERE status != 'INACTIVE'")
        dests = []
        for r in cursor:
            dests.append({'id': r[0], 'status': r[1], 'error': r[2], 'dest': r[3]})
        report['transport'] = dests
        conn_p.close()
    else:
        report['primary'] = "Unreachable"

    # Check Standby
    conn_s = get_connection(args, args.standby_host, args.sid)
    if conn_s:
        cursor = conn_s.cursor()
        cursor.execute("SELECT database_role, open_mode, switchover_status FROM v$database")
        row = cursor.fetchone()
        report['standby'] = {
            'role': row[0], 'mode': row[1], 'switchover': row[2]
        }
        
        # Check MRP
        cursor.execute("SELECT process, status, sequence#, block# FROM v$managed_standby WHERE process LIKE 'MRP%'")
        mrp = cursor.fetchone()
        if mrp:
            report['mrp'] = {'status': mrp[1], 'sequence': mrp[2]}
        else:
            report['mrp'] = "NOT RUNNING"
            
        # Check Lag
        try:
            cursor.execute("SELECT name, value FROM v$dataguard_stats")
            lags = {r[0]: r[1] for r in cursor}
            report['lag'] = lags
        except:
            report['lag'] = "Unavailable"
            
        conn_s.close()
    else:
        report['standby'] = "Unreachable"

    print(json.dumps(report, indent=2))

def optimize_adg(args):
    actions = []
    
    conn_p = get_connection(args, args.primary_host, args.sid)
    conn_s = get_connection(args, args.standby_host, args.sid)
    
    if not conn_p or not conn_s:
        print(json.dumps({"status": "error", "message": "Both nodes must be reachable."}))
        return

    try:
        # 1. Standby Redo Logs
        cursor_p = conn_p.cursor()
        cursor_s = conn_s.cursor()
        
        # Get Log Size
        cursor_p.execute("SELECT bytes FROM v$log WHERE rownum=1")
        log_size = cursor_p.fetchone()[0]
        
        # Count Online Groups
        cursor_p.execute("SELECT count(*) FROM v$log")
        online_groups = cursor_p.fetchone()[0]
        req_srls = online_groups + 1
        
        # Count SRLs
        cursor_s.execute("SELECT count(*) FROM v$standby_log")
        curr_srls = cursor_s.fetchone()[0]
        
        if curr_srls < req_srls:
            # Determine start group
            cursor_p.execute("SELECT max(group#) FROM v$logfile")
            max_p = cursor_p.fetchone()[0]
            cursor_s.execute("SELECT max(group#) FROM v$logfile")
            max_s = cursor_s.fetchone()[0]
            start_group = max(max_p, max_s) + 1
            
            # Stop MRP to add logs safely
            try:
                cursor_s.execute("ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL")
            except: pass
            
            needed = req_srls - curr_srls
            for i in range(needed):
                group = start_group + i
                sql = f"ALTER DATABASE ADD STANDBY LOGFILE GROUP {group} SIZE {log_size}"
                cursor_p.execute(sql)
                cursor_s.execute(sql)
                actions.append(f"Added SRL Group {group}")
                
        # 2. Flashback
        cursor_p.execute("SELECT flashback_on FROM v$database")
        if cursor_p.fetchone()[0] != 'YES':
            cursor_p.execute("ALTER SYSTEM SET db_recovery_file_dest_size=10G SCOPE=BOTH")
            cursor_p.execute("ALTER DATABASE FLASHBACK ON")
            actions.append("Enabled Flashback on Primary")
            
        cursor_s.execute("SELECT flashback_on FROM v$database")
        if cursor_s.fetchone()[0] != 'YES':
            cursor_s.execute("ALTER SYSTEM SET db_recovery_file_dest_size=10G SCOPE=BOTH")
            # MRP already stopped above if adding SRLs, else try stop
            try: cursor_s.execute("ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL")
            except: pass
            cursor_s.execute("ALTER DATABASE FLASHBACK ON")
            actions.append("Enabled Flashback on Standby")

        # 3. Real-Time Apply
        # Restart MRP
        try:
            cursor_s.execute("ALTER DATABASE RECOVER MANAGED STANDBY DATABASE DISCONNECT FROM SESSION USING CURRENT LOGFILE")
            actions.append("Restarted MRP with Real-Time Apply")
        except Exception as e:
            actions.append(f"MRP Restart Error: {str(e)}")

        print(json.dumps({"status": "success", "actions": actions}, indent=2))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
    finally:
        if conn_p: conn_p.close()
        if conn_s: conn_s.close()

def main():
    parser = argparse.ArgumentParser(description="Oracle ADG Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Common Args
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--primary-host", required=True)
    parent.add_argument("--standby-host", required=True)
    parent.add_argument("--port", default=1521)
    parent.add_argument("--sid", default='orcl')
    parent.add_argument("--user", default='sys')
    parent.add_argument("--password", required=True)
    
    p_check = subparsers.add_parser("check", parents=[parent], help="Check ADG Status")
    p_opt = subparsers.add_parser("optimize", parents=[parent], help="Optimize ADG Config")
    
    args = parser.parse_args()
    
    if args.command == "check":
        check_adg_status(args)
    elif args.command == "optimize":
        optimize_adg(args)

if __name__ == "__main__":
    main()
