import argparse
import oracledb
import json
import sys

def get_connection(args):
    if args.sid:
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={args.host})(PORT={args.port}))(CONNECT_DATA=(SID={args.sid})))"
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
    else:
        conn = oracledb.connect(user=args.user, password=args.password, 
                                host=args.host, port=args.port, service_name=args.service)
    return conn

def execute_query(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or [])
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(dict(zip(columns, row)))
        return result
    except Exception as e:
        return [{"error": str(e)}]

def inspect_system(conn):
    report = {}
    cursor = conn.cursor()

    # 1. Instance Overview
    report['instance'] = execute_query(cursor, """
        SELECT i.instance_name, i.host_name, i.version, i.status, d.name as db_name, 
               d.open_mode, d.log_mode, i.startup_time,
               FLOOR((SYSDATE - i.startup_time)) || ' days ' || 
               TRUNC(MOD((SYSDATE - i.startup_time) * 24, 24)) || ' hours' as uptime
        FROM v$instance i, v$database d
    """)

    # 2. Storage Health (Tablespaces)
    report['tablespace_usage'] = execute_query(cursor, """
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

    # 3. Top Objects in SYSTEM Tablespace (to investigate the 99% usage)
    report['top_system_objects'] = execute_query(cursor, """
        SELECT * FROM (
            SELECT owner, segment_name, segment_type, ROUND(bytes/1024/1024, 2) as size_mb 
            FROM dba_segments 
            WHERE tablespace_name = 'SYSTEM' 
            ORDER BY bytes DESC
        ) WHERE ROWNUM <= 10
    """)

    # 4. Performance: Top Wait Events
    report['top_wait_events'] = execute_query(cursor, """
        SELECT event, total_waits, time_waited, wait_class
        FROM v$system_event 
        WHERE wait_class != 'Idle' 
        ORDER BY time_waited DESC 
        FETCH FIRST 5 ROWS ONLY
    """)

    # 5. Database Health: Invalid Objects
    report['invalid_objects'] = execute_query(cursor, """
        SELECT owner, object_type, COUNT(*) as count 
        FROM dba_objects 
        WHERE status = 'INVALID' 
        GROUP BY owner, object_type 
        ORDER BY count DESC
    """)

    # 6. Database Configuration Risks
    report['config_risks'] = execute_query(cursor, """
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

    # 7. Backup Status (RMAN)
    report['rman_backups'] = execute_query(cursor, """
        SELECT input_type, status, 
               TO_CHAR(start_time, 'YYYY-MM-DD HH24:MI') as start_time, 
               time_taken_display
        FROM v$rman_backup_job_details 
        WHERE start_time > SYSDATE - 7 
        ORDER BY start_time DESC
        FETCH FIRST 5 ROWS ONLY
    """)

    # 8. Resource Limit Usage (High Water Mark)
    report['resource_limits'] = execute_query(cursor, """
        SELECT resource_name, current_utilization, max_utilization, limit_value,
               ROUND(max_utilization / TO_NUMBER(limit_value) * 100, 1) as max_usage_pct
        FROM v$resource_limit 
        WHERE limit_value != ' UNLIMITED' 
          AND TO_NUMBER(limit_value) > 0
          AND (max_utilization / TO_NUMBER(limit_value)) > 0.5
        ORDER BY max_usage_pct DESC
    """)

    return report

def main():
    parser = argparse.ArgumentParser(description="Oracle Deep Inspection Tool")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", default="1521")
    parser.add_argument("--service")
    parser.add_argument("--sid")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)

    args = parser.parse_args()

    try:
        conn = get_connection(args)
        report = inspect_system(conn)
        
        # Output JSON for machine reading, but normally we might want a pretty text report.
        # For Gemini CLI, JSON is great because I can parse it and narrate.
        print(json.dumps(report, indent=2, default=str))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
