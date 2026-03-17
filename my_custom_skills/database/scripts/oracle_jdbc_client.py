import argparse
import jaydebeapi
import json
import sys
import os
import traceback

def get_connection(args):
    if args.sid:
        jdbc_url = f"jdbc:oracle:thin:@{args.host}:{args.port}:{args.sid}"
    else:
        jdbc_url = f"jdbc:oracle:thin:@//{args.host}:{args.port}/{args.service}"
    
    driver_class = "oracle.jdbc.driver.OracleDriver"
    
    # Check if jar exists
    if not os.path.exists(args.driver_jar):
        raise FileNotFoundError(f"Driver JAR not found at: {args.driver_jar}")

    # Connect
    conn = jaydebeapi.connect(
        driver_class,
        jdbc_url,
        [args.user, args.password],
        args.driver_jar
    )
    return conn

def handle_query(cursor, sql):
    cursor.execute(sql)
    
    # Fetch column names
    if cursor.description:
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            # Convert row to dict, handling potential non-serializable types roughly
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # specific type handling could go here
                row_dict[col] = str(val) if val is not None else None
            result.append(row_dict)
            
        return result
    else:
        return {"status": "executed", "rowcount": cursor.rowcount}

def main():
    parser = argparse.ArgumentParser(description="Oracle JDBC Client")
    parser.add_argument("--action", choices=["test", "query"], required=True, help="Action to perform")
    parser.add_argument("--host", required=True, help="Database Host")
    parser.add_argument("--port", default="1521", help="Database Port")
    parser.add_argument("--service", help="Service Name")
    parser.add_argument("--sid", help="SID")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--driver-jar", required=True, help="Path to ojdbc*.jar")
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
                print(json.dumps({"status": "success", "message": "Connection successful"}))
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
