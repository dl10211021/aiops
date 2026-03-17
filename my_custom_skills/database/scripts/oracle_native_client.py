import argparse
import oracledb
import json
import sys
import traceback

def get_connection(args):
    # oracledb Thin mode doesn't need Oracle Client
    if args.sid:
        # For SID, use the older DSN format or construct a connect descriptor
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={args.host})(PORT={args.port}))(CONNECT_DATA=(SID={args.sid})))"
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
    else:
        # For Service Name
        conn = oracledb.connect(user=args.user, password=args.password, 
                                host=args.host, port=args.port, service_name=args.service)
    conn.autocommit = True
    return conn

def handle_query(cursor, sql):
    cursor.execute(sql)
    
    if cursor.description:
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Handle common non-serializable types if necessary
                row_dict[col] = str(val) if val is not None else None
            result.append(row_dict)
            
        return result
    else:
        return {"status": "executed", "rowcount": cursor.rowcount}

def main():
    parser = argparse.ArgumentParser(description="Oracle Native Client (Thin Mode)")
    parser.add_argument("--action", choices=["test", "query"], required=True, help="Action to perform")
    parser.add_argument("--host", required=True, help="Database Host")
    parser.add_argument("--port", default="1521", help="Database Port")
    parser.add_argument("--service", help="Service Name")
    parser.add_argument("--sid", help="SID")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--sql", help="SQL Query to execute (required for action=query)")

    args = parser.parse_args()

    if not args.service and not args.sid:
        print(json.dumps({"error": "Either --service or --sid must be provided"}))
        sys.exit(1)

    conn = None
    try:
        conn = get_connection(args)
        curs = conn.cursor()

        if args.action == "test":
            curs.execute("SELECT 1 FROM DUAL")
            one = curs.fetchone()
            if one and str(one[0]) == "1":
                print(json.dumps({"status": "success", "message": "Connection successful (Thin Mode)"}))
            else:
                print(json.dumps({"status": "failed", "message": "Connection test returned unexpected result"}))

        elif args.action == "query":
            if not args.sql:
                print(json.dumps({"error": "SQL argument required for query action"}))
                sys.exit(1)
            
            result = handle_query(curs, args.sql)
            print(json.dumps(result, indent=2))

    except Exception as e:
        error_msg = {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
        print(json.dumps(error_msg, indent=2))
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
