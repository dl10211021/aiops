import argparse
import oracledb
import csv
import json
import sys
import os

def get_connection(args):
    if args.sid:
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={args.host})(PORT={args.port}))(CONNECT_DATA=(SID={args.sid})))"
        conn = oracledb.connect(user=args.user, password=args.password, dsn=dsn)
    else:
        conn = oracledb.connect(user=args.user, password=args.password, 
                                host=args.host, port=args.port, service_name=args.service)
    return conn

def main():
    parser = argparse.ArgumentParser(description="Oracle Data Exporter")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", default="1521")
    parser.add_argument("--service")
    parser.add_argument("--sid")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--table", required=True, help="Table name to export (schema.table)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    if not args.service and not args.sid:
        print("Error: Either --service or --sid must be provided")
        sys.exit(1)

    output_file = args.output or f"{args.table.replace('.', '_')}_export.{args.format}"

    try:
        conn = get_connection(args)
        curs = conn.cursor()
        
        # Check if table exists and get columns
        query = f"SELECT * FROM {args.table}"
        curs.execute(query)
        
        columns = [desc[0] for desc in curs.description]
        
        if args.format == "csv":
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in curs:
                    writer.writerow(row)
            print(f"Successfully exported to CSV: {output_file}")
            
        elif args.format == "json":
            data = []
            for row in curs:
                data.append(dict(zip(columns, [str(x) if x is not None else None for x in row])))
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Successfully exported to JSON: {output_file}")

    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
