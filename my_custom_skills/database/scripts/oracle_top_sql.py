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

def get_top_sql(conn, limit=5):
    report = {}
    cursor = conn.cursor()

    # 1. Top SQL by Elapsed Time (Total)
    # Good for finding long-running jobs or cumulative impact
    report['top_elapsed_time'] = execute_query(cursor, f"""
        SELECT sql_id, executions, 
               ROUND(elapsed_time/1000000, 2) as total_elapsed_sec,
               ROUND(elapsed_time/1000000/GREATEST(executions, 1), 4) as avg_elapsed_sec,
               ROUND(cpu_time/1000000, 2) as cpu_sec,
               sql_text
        FROM v$sqlstats
        ORDER BY elapsed_time DESC
        FETCH FIRST {limit} ROWS ONLY
    """)

    # 2. Top SQL by CPU (CPU Burners)
    report['top_cpu'] = execute_query(cursor, f"""
        SELECT sql_id, executions, 
               ROUND(cpu_time/1000000, 2) as total_cpu_sec,
               ROUND(cpu_time/1000000/GREATEST(executions, 1), 4) as avg_cpu_sec,
               sql_text
        FROM v$sqlstats
        ORDER BY cpu_time DESC
        FETCH FIRST {limit} ROWS ONLY
    """)

    # 3. Top SQL by Logical Reads (Buffer Gets) - High CPU/Latch contention candidates
    report['top_buffer_gets'] = execute_query(cursor, f"""
        SELECT sql_id, executions, 
               buffer_gets as total_gets,
               ROUND(buffer_gets/GREATEST(executions, 1), 2) as gets_per_exec,
               sql_text
        FROM v$sqlstats
        ORDER BY buffer_gets DESC
        FETCH FIRST {limit} ROWS ONLY
    """)

    # 4. Top SQL by Physical Reads (Disk I/O) - I/O Bottlenecks
    report['top_disk_reads'] = execute_query(cursor, f"""
        SELECT sql_id, executions, 
               disk_reads as total_disk_reads,
               ROUND(disk_reads/GREATEST(executions, 1), 2) as reads_per_exec,
               sql_text
        FROM v$sqlstats
        ORDER BY disk_reads DESC
        FETCH FIRST {limit} ROWS ONLY
    """)

    return report

def main():
    parser = argparse.ArgumentParser(description="Oracle Top SQL Analyzer")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", default="1521")
    parser.add_argument("--service")
    parser.add_argument("--sid")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--limit", type=int, default=5, help="Number of rows per category")

    args = parser.parse_args()

    try:
        conn = get_connection(args)
        report = get_top_sql(conn, args.limit)
        print(json.dumps(report, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
