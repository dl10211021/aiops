import argparse
import sys
import os

# Add parent directory to path to import manage_engine_api
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def main():
    parser = argparse.ArgumentParser(description="Manage Maintenance Tasks and Monitor State in Applications Manager.")
    parser.add_argument("resource", help="Resource ID or IP address/Name of the monitor")
    parser.add_argument("--action", choices=["manage", "unmanage", "schedule", "details"], default="details",
                        help="Action to perform")
    parser.add_argument("--name", help="Task name for schedule")
    parser.add_argument("--start", default="02:00", help="Start time (HH:mm)")
    parser.add_argument("--end", default="04:00", help="End time (HH:mm)")
    parser.add_argument("--method", choices=["once", "daily", "weekly", "monthly"], default="daily", help="Recurrence")
    
    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    # Resolve resource ID if IP/Name is provided
    resource_id = args.resource
    if not resource_id.isdigit():
        print(f"[INFO] Searching for resource ID for '{args.resource}'...")
        monitors = client.list_monitors()
        found = False
        if monitors and 'response' in monitors:
            for m in monitors['response']['result']:
                if m['DISPLAYNAME'] == args.resource or m.get('HOSTIP') == args.resource or m.get('HOSTNAME') == args.resource:
                    resource_id = m['RESOURCEID']
                    print(f"[SUCCESS] Found ResourceID: {resource_id} for {m['DISPLAYNAME']}")
                    found = True
                    break
        if not found:
            print(f"[ERROR] Could not find resource ID for '{args.resource}'")
            sys.exit(1)

    if args.action == "details":
        print(f"--- Downtime Details for {resource_id} ---")
        details = client.get_downtime_details(resource_id)
        import json
        print(json.dumps(details, indent=2))
        
    elif args.action in ["manage", "unmanage"]:
        print(f"[INFO] Setting state to {args.action} for {resource_id}...")
        result = client.manage_monitor(resource_id, action=args.action)
        print(result)
        
    elif args.action == "schedule":
        if not args.name:
            print("[ERROR] --name is required for scheduling")
            sys.exit(1)
        print(f"[INFO] Creating maintenance task '{args.name}' for {resource_id} ({args.start} to {args.end})...")
        result = client.create_maintenance_task(args.name, resource_id, args.start, args.end, method=args.method)
        print(result)

if __name__ == "__main__":
    main()
