
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('add_linux_monitor')

def main():
    parser = argparse.ArgumentParser(description="Add Linux Monitor to AppManager")
    parser.add_argument("ip", help="IP address of the Linux server")
    parser.add_argument("user", help="SSH username")
    parser.add_argument("password", help="SSH password")
    parser.add_argument("--name", help="Display name for the monitor (default: Linux_IP)", default=None)
    parser.add_argument("--group", help="Monitor Group ID to associate with (e.g., 100000123)", default=None)
    parser.add_argument("--poll", type=int, default=300, help="Polling Interval in seconds (Default: 300)")
    parser.add_argument("--agent", help="Managed Server ID (Probe ID) for distributed setups", default=None)
    parser.add_argument("--label", help="Label to assign to the monitor", default=None)
    
    args = parser.parse_args()

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info(f"Adding Linux Monitor: {args.ip}")
    if args.name:
        logger.info(f"Display Name: {args.name}")
    if args.group:
        logger.info(f"Adding to Group ID: {args.group}")

    try:
        response = client.add_linux_monitor(
            ip=args.ip,
            user=args.user,
            password=args.password,
            display_name=args.name,
            group_id=args.group,
            poll_interval=args.poll,
            managed_server_id=args.agent,
            label=args.label
        )
        
        logger.info(f"API Response: {response}")
        
        if response and 'response-code' in response and response['response-code'] == '4000':
            resource_id = response.get('resourceid', 'Unknown')
            logger.info(f"Successfully added monitor. Resource ID: {resource_id}")
            print(f"SUCCESS: Monitor added with ID {resource_id}")
        else:
            error_msg = response.get('response', {}).get('message', 'Unknown error') if response else "Empty response"
            logger.error(f"Failed to add monitor: {error_msg}")
            print(f"ERROR: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error adding monitor: {e}")
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
