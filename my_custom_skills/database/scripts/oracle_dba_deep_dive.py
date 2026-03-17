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

def dba_deep_dive(conn):
    report = {}
    cursor = conn.cursor()

    # 1. SYSAUX Analysis (Why is it full?)
    report['sysaux_occupants'] = execute_query(cursor, """
        SELECT occupant_name, schema_name, move_procedure,
               ROUND(space_usage_kbytes/1024, 2) as space_mb
        FROM v$sysaux_occupants
        ORDER BY space_usage_kbytes DESC
        FETCH FIRST 5 ROWS ONLY
    """)

    # 2. Redo Log Switch Frequency (Last 24 hours)
    # High frequency (> 4-6 per hour) implies log files are too small
    report['log_switches'] = execute_query(cursor, """
        SELECT COUNT(*) as switches_last_24h,
               ROUND(COUNT(*)/24, 2) as avg_switches_per_hour
        FROM v$log_history
        WHERE first_time > SYSDATE - 1
    """)

    # 3. Memory Performance (Buffer Cache & Library Cache Hit Ratios)
    report['memory_ratios'] = execute_query(cursor, """
        SELECT 
            (SELECT ROUND((1 - (phy.value / (cur.value + con.value))) * 100, 2)
             FROM v$sysstat cur, v$sysstat con, v$sysstat phy
             WHERE cur.name = 'db block gets'
               AND con.name = 'consistent gets'
               AND phy.name = 'physical reads') AS buffer_cache_hit_ratio,
            (SELECT ROUND(SUM(pinhits)/SUM(pins) * 100, 2) 
             FROM v$librarycache) AS library_cache_hit_ratio,
             (SELECT ROUND(SUM(gets - getmisses) * 100 / SUM(gets), 2)
              FROM v$rowcache) AS dictionary_cache_hit_ratio
        FROM dual
    """)

    # 4. User Security (Default Passwords & Locked Accounts)
    # Checking for accounts that are OPEN but might be standard default accounts
    report['user_security'] = execute_query(cursor, """
        SELECT username, account_status, expiry_date, profile
        FROM dba_users
        WHERE account_status = 'OPEN'
          AND username IN ('SCOTT', 'HR', 'OE', 'SH', 'PM', 'IX', 'BI', 'DBSNMP')
    """)

    # 5. AWR Retention Settings (Often the cause of SYSAUX bloat)
    report['awr_settings'] = execute_query(cursor, """
        SELECT extract(day from retention) || ' days ' || 
               extract(hour from retention) || ' hours' as retention_period,
               extract(day from snap_interval) * 24 * 60 + 
               extract(hour from snap_interval) * 60 + 
               extract(minute from snap_interval) as snap_interval_mins
        FROM dba_hist_wr_control
    """)
    
    # 6. Temp Usage
    report['temp_usage'] = execute_query(cursor, """
        SELECT d.tablespace_name, 
               ROUND(NVL(a.bytes / 1024 / 1024, 0), 2) as allocated_mb,
               ROUND(NVL(t.bytes, 0) / 1024 / 1024, 2) as used_mb
        FROM dba_temp_files d
        LEFT JOIN (SELECT tablespace_name, SUM(bytes) bytes 
                   FROM dba_temp_files GROUP BY tablespace_name) a 
                   ON d.tablespace_name = a.tablespace_name
        LEFT JOIN (SELECT tablespace_name, SUM(bytes_used) bytes 
                   FROM v$temp_extent_pool GROUP BY tablespace_name) t 
                   ON d.tablespace_name = t.tablespace_name
        GROUP BY d.tablespace_name, a.bytes, t.bytes
    """)

    return report

def main():
    parser = argparse.ArgumentParser(description="Oracle DBA Deep Dive")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", default="1521")
    parser.add_argument("--service")
    parser.add_argument("--sid")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)

    args = parser.parse_args()

    try:
        conn = get_connection(args)
        report = dba_deep_dive(conn)
        print(json.dumps(report, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
