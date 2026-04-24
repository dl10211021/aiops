import pymysql
import argparse
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_db(args):
    try:
        conn = pymysql.connect(
            host=args.host,
            user=args.user,
            password=args.password,
            port=args.port,
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info(f"Connected to MySQL at {args.host}:{args.port}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        sys.exit(1)

def check_version(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT VERSION() as version")
        ver = cursor.fetchone()['version']
        logger.info(f"Detected MySQL Version: {ver}")
        if not ver.startswith('8.0'):
            logger.warning("This tool is optimized for upgrading from MySQL 8.0. Use with caution.")
        return ver

def check_auth_plugins(conn):
    issues = []
    fixes = []
    logger.info("Checking for deprecated authentication plugins (mysql_native_password)...")
    
    query = """
    SELECT user, host, plugin 
    FROM mysql.user 
    WHERE plugin = 'mysql_native_password'
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if rows:
            logger.warning(f"Found {len(rows)} users using 'mysql_native_password'. This plugin is removed in MySQL 8.4.")
            for row in rows:
                user_host = f"'{row['user']}'@'{row['host']}'"
                issues.append(f"User {user_host} uses deprecated plugin.")
                # Generate fix: Switch to caching_sha2_password
                # Note: We can't generate the exact password command without knowing the password, 
                # but we can generate the ALTER template.
                fixes.append(f"-- ACTION REQUIRED: Update password for {user_host}")
                fixes.append(f"ALTER USER {user_host} IDENTIFIED WITH caching_sha2_password BY 'replace_with_password';")
        else:
            logger.info("No users found using 'mysql_native_password'.")
            
    return issues, fixes

def check_charsets(conn):
    issues = []
    fixes = []
    logger.info("Checking for deprecated 'utf8mb3' (often aliased as 'utf8') usage...")
    
    # Check Tables
    query = """
    SELECT table_schema, table_name, table_collation 
    FROM information_schema.tables 
    WHERE table_collation LIKE 'utf8_%%' OR table_collation LIKE 'utf8mb3_%%'
    AND table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if rows:
            logger.warning(f"Found {len(rows)} tables using utf8mb3/utf8.")
            for row in rows:
                tbl = f"{row['table_schema']}.{row['table_name']}"
                issues.append(f"Table {tbl} uses collation {row['table_collation']}.")
                fixes.append(f"ALTER TABLE {tbl} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
        else:
            logger.info("No user tables found using deprecated utf8mb3.")

    return issues, fixes

def check_replication_config(conn):
    issues = []
    fixes = []
    logger.info("Checking replication configuration (GTID, Binlog Format)...")
    
    vars_to_check = ['gtid_mode', 'binlog_format', 'lower_case_table_names']
    config = {}
    
    with conn.cursor() as cursor:
        for var in vars_to_check:
            cursor.execute(f"SHOW VARIABLES LIKE '{var}'")
            res = cursor.fetchone()
            if res:
                config[var] = res['Value']
    
    # Check GTID
    if config.get('gtid_mode') != 'ON':
        issues.append(f"GTID_MODE is {config.get('gtid_mode')}. Recommend ON for safer upgrades/failover.")
        fixes.append("-- WARNING: GTID_MODE is not ON. Review your replication topology strategy.")
        fixes.append("-- Ideally: ENFORCE_GTID_CONSISTENCY = ON, then GTID_MODE = ON.")

    # Check Binlog Format
    if config.get('binlog_format') != 'ROW':
        issues.append(f"BINLOG_FORMAT is {config.get('binlog_format')}. Recommend ROW for compatibility and data integrity.")
        fixes.append("SET GLOBAL binlog_format = 'ROW'; -- Requires checking downstream compatibility")
        
    return issues, fixes

def main():
    parser = argparse.ArgumentParser(description="MySQL 8.0 -> 8.4 Upgrade Assessor")
    parser.add_argument('--host', required=True, help='Database Host')
    parser.add_argument('--port', type=int, default=3306, help='Database Port')
    parser.add_argument('--user', required=True, help='Database User')
    parser.add_argument('--password', required=True, help='Database Password')
    
    args = parser.parse_args()
    
    conn = connect_db(args)
    
    try:
        check_version(conn)
        
        all_issues = []
        all_fixes = []
        
        # Run Checks
        i, f = check_auth_plugins(conn)
        all_issues.extend(i)
        all_fixes.extend(f)
        
        i, f = check_charsets(conn)
        all_issues.extend(i)
        all_fixes.extend(f)
        
        i, f = check_replication_config(conn)
        all_issues.extend(i)
        all_fixes.extend(f)
        
        # Report
        print("\n" + "="*60)
        print(" UPGRADE ASSESSMENT REPORT ")
        print("="*60)
        
        if all_issues:
            print(f"\nFound {len(all_issues)} potential blocking issues or warnings:")
            for idx, issue in enumerate(all_issues, 1):
                print(f"{idx}. {issue}")
        else:
            print("\nNo major blocking issues found! (Standard checks only)")
            
        print("\n" + "="*60)
        print(" GENERATED REMEDIATION SCRIPT (Review carefully!) ")
        print("="*60)
        
        if all_fixes:
            print("\n".join(all_fixes))
        else:
            print("-- No remediation actions generated.")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()
