
import sys
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ops_tool')

def main():
    parser = argparse.ArgumentParser(description="ManageEngine Operations Tool (Poll, Action, Groups)")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command")

    # --- Poll Now ---
    poll_parser = subparsers.add_parser("poll", help="Trigger Immediate Poll")
    poll_parser.add_argument("resource_id", help="Resource ID to Poll")

    # --- Execute Action ---
    action_parser = subparsers.add_parser("action", help="Execute Action on Resource")
    action_parser.add_argument("action_id", help="Action ID to Execute")
    action_parser.add_argument("resource_id", help="Target Resource ID")

    # --- Group Management ---
    group_parser = subparsers.add_parser("group", help="Manage Monitor Groups")
    group_sub = group_parser.add_subparsers(dest="subcommand", required=True)
    
    # Add Group
    add_group = group_sub.add_parser("add", help="Create Group")
    add_group.add_argument("name", help="Group Name")
    add_group.add_argument("--desc", help="Description")

    # Delete Group
    del_group = group_sub.add_parser("delete", help="Delete Group")
    del_group.add_argument("id", help="Group ID")
    
    # Associate
    assoc = group_sub.add_parser("associate", help="Add Monitor to Group")
    assoc.add_argument("resource_id", help="Monitor Resource ID")
    assoc.add_argument("group_id", help="Target Group ID")
    
    # Unassociate
    unassoc = group_sub.add_parser("unassociate", help="Remove Monitor from Group")
    unassoc.add_argument("resource_id", help="Monitor Resource ID")
    unassoc.add_argument("group_id", help="Target Group ID")

    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    try:
        response = None
        
        if args.command == "poll":
            logger.info(f"Triggering Poll for {args.resource_id}...")
            response = client.poll_now(args.resource_id)
            
        elif args.command == "action":
            logger.info(f"Executing Action {args.action_id} on {args.resource_id}...")
            response = client.execute_action(args.action_id, args.resource_id)
            
        elif args.command == "group":
            if args.subcommand == "add":
                logger.info(f"Creating Group: {args.name}")
                response = client.add_monitor_group(args.name, args.desc)
            elif args.subcommand == "delete":
                logger.info(f"Deleting Group ID: {args.id}")
                response = client.delete_monitor_group(args.id)
            elif args.subcommand == "associate":
                logger.info(f"Associating {args.resource_id} to Group {args.group_id}")
                response = client.associate_monitor_to_group(args.resource_id, args.group_id)
            elif args.subcommand == "unassociate":
                logger.info(f"Unassociating {args.resource_id} from Group {args.group_id}")
                response = client.unassociate_monitor_from_group(args.resource_id, args.group_id)

        # Output Result
        if response:
            logger.info(f"API Response: {response}")
            
            if isinstance(response, dict):
                # JSON Handling
                res_data = response.get('response', response)
                res_code = res_data.get('response-code')
                if str(res_code) == '4000':
                     print("[SUCCESS] Operation completed successfully.")
                else:
                     print(f"[ERROR] API returned code: {res_code}")
                     import json
                     print(json.dumps(response, indent=2))
            elif isinstance(response, str):
                # XML Handling (Simple check)
                if 'response-code="4000"' in response:
                    print("[SUCCESS] Operation completed successfully.")
                    # Extract message if possible
                    if "<message>" in response:
                        import re
                        msg = re.search(r"<message>(.*?)</message>", response)
                        if msg:
                            print(f"Message: {msg.group(1)}")
                else:
                    print("[INFO] Raw Response:")
                    print(response)
        else:
            print("[ERROR] No response from API.")

    except Exception as e:
        logger.error(f"Operation Failed: {e}")
        print(f"[CRITICAL] Error: {e}")

if __name__ == "__main__":
    main()
