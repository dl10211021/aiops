import argparse
import pymysql
import json
import csv
import sys
import datetime

def get_connection(args):
    try:
        conn = pymysql.connect(
            host=args.host,
            port=int(args.port),
            user=args.user,
            password=args.password,
            database=args.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

def execute_query(conn, sql):
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("SHOW") or sql.strip().upper().startswith("DESC"):
                result = cursor.fetchall()
                # Handle date/time objects for JSON serialization
                for row in result:
                    for key, value in row.items():
                        if isinstance(value, (datetime.date, datetime.datetime)):
                            row[key] = value.isoformat()
                        elif isinstance(value, datetime.timedelta):
                            row[key] = str(value)
                return result
            else:
                conn.commit()
                return {"status": "success", "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def action_query(conn, args):
    result = execute_query(conn, args.sql)
    print(json.dumps(result, indent=2, ensure_ascii=False))

def action_list_tables(conn, args):
    result = execute_query(conn, "SHOW TABLES")
    tables = [list(row.values())[0] for row in result]
    print(json.dumps(tables, indent=2))

def action_describe(conn, args):
    result = execute_query(conn, f"DESCRIBE `{args.table}`")
    print(json.dumps(result, indent=2))

def action_export(conn, args):
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{args.table}`")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            filename = f"{args.table}_export.{args.format}"
            
            if args.format == 'csv':
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    for row in rows:
                        writer.writerow([row[col] for col in columns])
            elif args.format == 'json':
                data = []
                for row in rows:
                    item = {}
                    for col in columns:
                        val = row[col]
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            val = val.isoformat()
                        item[col] = val
                    data.append(item)
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(json.dumps({"status": "success", "file": filename}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def main():
    parser = argparse.ArgumentParser(description="MySQL Client Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common Args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--host", required=True)
    parent_parser.add_argument("--port", default="3306")
    parent_parser.add_argument("--user", required=True)
    parent_parser.add_argument("--password", required=True)
    parent_parser.add_argument("--database", required=True)

    # Commands
    p_query = subparsers.add_parser("query", parents=[parent_parser], help="Execute SQL")
    p_query.add_argument("--sql", required=True)

    p_list = subparsers.add_parser("list-tables", parents=[parent_parser], help="List Tables")

    p_desc = subparsers.add_parser("describe", parents=[parent_parser], help="Describe Table Structure")
    p_desc.add_argument("--table", required=True)

    p_export = subparsers.add_parser("export", parents=[parent_parser], help="Export Data")
    p_export.add_argument("--table", required=True)
    p_export.add_argument("--format", choices=['csv', 'json'], default='csv')

    args = parser.parse_args()
    conn = get_connection(args)

    try:
        if args.command == "query":
            action_query(conn, args)
        elif args.command == "list-tables":
            action_list_tables(conn, args)
        elif args.command == "describe":
            action_describe(conn, args)
        elif args.command == "export":
            action_export(conn, args)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
