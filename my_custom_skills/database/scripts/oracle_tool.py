import argparse
import oracledb
import json
import sys
import csv
import datetime
import os

# --- Database Connection ---
def get_connection(args):
    try:
        if args.sid:
            dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={args.host})(PORT={args.port}))(CONNECT_DATA=(SID={args.sid})))"
            conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
        else:
            conn = oracledb.connect(user=args.user, password=args.password, 
                                    host=args.host, port=args.port, service_name=args.service)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

def execute_query_as_dict(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or [])
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            result = []
            for row in rows:
                # Handle non-serializable types roughly
                clean_row = []
                for val in row:
                    if isinstance(val, datetime.datetime):
                        clean_row.append(val.isoformat())
                    elif isinstance(val, datetime.timedelta):
                        clean_row.append(str(val))
                    else:
                        clean_row.append(val)
                result.append(dict(zip(columns, clean_row)))
            return result
        return {"status": "executed", "rowcount": cursor.rowcount}
    except Exception as e:
        return [{"error": str(e)}]

# --- Actions ---

def action_query(conn, args):
    cursor = conn.cursor()
    result = execute_query_as_dict(cursor, args.sql)
    print(json.dumps(result, indent=2, default=str))

def action_export(conn, args):
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {args.table}")
        columns = [d[0] for d in cursor.description]
        
        output_file = args.output or f"{args.table.replace('.', '_')}_export.{args.format}"
        
        if args.format == "csv":
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in cursor:
                    writer.writerow(row)
        elif args.format == "json":
            data = []
            for row in cursor:
                data.append(dict(zip(columns, [str(x) if x is not None else None for x in row])))
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        print(json.dumps({"status": "success", "file": output_file}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def action_inspect(conn, args):
    report = {}
    cursor = conn.cursor()
    
    # Instance
    report['instance'] = execute_query_as_dict(cursor, """
        SELECT i.instance_name, i.host_name, i.version, i.status, d.name as db_name, 
               d.open_mode, d.log_mode, 
               FLOOR((SYSDATE - i.startup_time)) || ' days ' || 
               TRUNC(MOD((SYSDATE - i.startup_time) * 24, 24)) || ' hours' as uptime
        FROM v$instance i, v$database d
    """)
    
    # Storage (Tablespaces)
    report['storage'] = execute_query_as_dict(cursor, """
        SELECT df.tablespace_name, 
               ROUND(df.total_mb, 2) AS total_mb, 
               ROUND(df.total_mb - fs.free_mb, 2) AS used_mb, 
               ROUND(fs.free_mb, 2) AS free_mb, 
               ROUND((df.total_mb - fs.free_mb) / df.total_mb * 100, 2) AS usage_pct
        FROM (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS total_mb 
              FROM dba_data_files GROUP BY tablespace_name) df 
        LEFT JOIN (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS free_mb 
                   FROM dba_free_space GROUP BY tablespace_name) fs 
        ON df.tablespace_name = fs.tablespace_name 
        ORDER BY usage_pct DESC
    """)
    
    # Wait Events
    report['waits'] = execute_query_as_dict(cursor, """
        SELECT event, total_waits, time_waited, wait_class
        FROM v$system_event 
        WHERE wait_class != 'Idle' 
        ORDER BY time_waited DESC 
        FETCH FIRST 5 ROWS ONLY
    """)
    
    # Invalid Objects
    report['invalid_objects'] = execute_query_as_dict(cursor, """
        SELECT owner, object_type, COUNT(*) as count 
        FROM dba_objects 
        WHERE status = 'INVALID' 
        GROUP BY owner, object_type 
        ORDER BY count DESC
    """)

    # Config Risks
    report['risks'] = execute_query_as_dict(cursor, """
        SELECT 'Force Logging' as check_item, force_logging as value, 
               CASE WHEN force_logging = 'YES' THEN 'PASS' ELSE 'WARNING' END as status
        FROM v$database
        UNION ALL
        SELECT 'Redo Log Groups', TO_CHAR(COUNT(*)), 
               CASE WHEN COUNT(*) >= 3 THEN 'PASS' ELSE 'WARNING' END 
        FROM v$log
        UNION ALL
        SELECT 'Control Files', TO_CHAR(COUNT(*)), 
               CASE WHEN COUNT(*) >= 2 THEN 'PASS' ELSE 'CRITICAL' END 
        FROM v$controlfile
    """)
    
    print(json.dumps(report, indent=2, default=str))

def action_top_sql(conn, args):
    limit = args.limit or 5
    cursor = conn.cursor()
    report = {}
    
    # By Time
    report['by_time'] = execute_query_as_dict(cursor, f"""
        SELECT sql_id, executions, 
               ROUND(elapsed_time/1000000, 2) as total_sec,
               ROUND(elapsed_time/1000000/GREATEST(executions, 1), 4) as avg_sec,
               sql_text
        FROM v$sqlstats ORDER BY elapsed_time DESC FETCH FIRST {limit} ROWS ONLY
    """)
    
    # By CPU
    report['by_cpu'] = execute_query_as_dict(cursor, f"""
        SELECT sql_id, executions, 
               ROUND(cpu_time/1000000, 2) as cpu_sec,
               sql_text
        FROM v$sqlstats ORDER BY cpu_time DESC FETCH FIRST {limit} ROWS ONLY
    """)
    
    print(json.dumps(report, indent=2, default=str))

# --- Main CLI ---

def main():
    parser = argparse.ArgumentParser(description="Gemini Oracle Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common Args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--host", required=True)
    parent_parser.add_argument("--port", default="1521")
    parent_parser.add_argument("--service")
    parent_parser.add_argument("--sid")
    parent_parser.add_argument("--user", required=True)
    parent_parser.add_argument("--password", required=True)

    # Command: Query
    p_query = subparsers.add_parser("query", parents=[parent_parser], help="Execute SQL")
    p_query.add_argument("--sql", required=True, help="SQL Query")

    # Command: Export
    p_export = subparsers.add_parser("export", parents=[parent_parser], help="Export Table")
    p_export.add_argument("--table", required=True)
    p_export.add_argument("--format", choices=["csv", "json"], default="csv")
    p_export.add_argument("--output", help="Output path")

    # Command: Inspect
    p_inspect = subparsers.add_parser("inspect", parents=[parent_parser], help="Deep Health Inspection")

    # Command: Top SQL
    p_top = subparsers.add_parser("top-sql", parents=[parent_parser], help="Top SQL Analysis")
    p_top.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    if not args.service and not args.sid:
        print(json.dumps({"error": "Either --service or --sid must be provided"}))
        sys.exit(1)

    conn = get_connection(args)
    
    try:
        if args.command == "query":
            action_query(conn, args)
        elif args.command == "export":
            action_export(conn, args)
        elif args.command == "inspect":
            action_inspect(conn, args)
        elif args.command == "top-sql":
            action_top_sql(conn, args)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
