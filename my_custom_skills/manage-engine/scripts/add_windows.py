
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('add_windows_monitor')

def main():
    parser = argparse.ArgumentParser(description="Add Windows Monitor to AppManager (WMI/SNMP)")
    parser.add_argument("host", help="Hostname or IP address of the Windows server")
    parser.add_argument("user", help=r"Username (Domain\User or User)")
    parser.add_argument("password", help="Password")
    parser.add_argument("--mode", choices=["WMI", "SNMP"], default="WMI", help="Monitoring Mode (Default: WMI)")
    parser.add_argument("--name", help="Display name for the monitor (default: Windows_Host)", default=None)
    parser.add_argument("--group", help="Monitor Group ID to associate with", default=None)
    parser.add_argument("--poll", type=int, default=300, help="Polling Interval in seconds (Default: 300)")
    parser.add_argument("--agent", help="Managed Server ID (Probe ID) for distributed setups", default=None)
    parser.add_argument("--label", help="Label to assign to the monitor", default=None)
    
    # SNMP Specific Args
    parser.add_argument("--community", default="public", help="SNMP Community String (Required for SNMP)")
    parser.add_argument("--port", default="161", help="SNMP Port (Default: 161)")

    args = parser.parse_args()

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info(f"Adding Windows Monitor: {args.host} ({args.mode})")
    if args.group:
        logger.info(f"Target Group: {args.group}")
    
    try:
        response = client.add_windows_monitor(
            host=args.host,
            user=args.user,
            password=args.password,
            mode=args.mode,
            display_name=args.name,
            group_id=args.group,
            poll_interval=args.poll,
            snmp_community=args.community,
            snmp_port=args.port,
            managed_server_id=args.agent,
            label=args.label
        )
        
        # Parse Response
        logger.info(f"API Response: {response}")
        
        res_data = response.get('response', response)
        res_code = res_data.get('response-code')
        res_msg = res_data.get('message', 'Unknown status')
        
        if str(res_code) == '4000':
            new_id = res_data.get('resourceid', 'N/A')
            print(f"[SUCCESS] Windows Monitor added. ID: {new_id}")
            print(f"          Message: {res_msg}")
        else:
            print(f"[ERROR] Failed to add monitor. Code: {res_code}")
            print(f"        Message: {res_msg}")

    except Exception as e:
        logger.error(f"Error adding monitor: {e}")
        print(f"[CRITICAL] Script Error: {e}")

if __name__ == "__main__":
    main()
