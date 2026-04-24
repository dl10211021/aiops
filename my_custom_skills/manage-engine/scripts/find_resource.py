
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('find_resource')

def find_resource(query, search_type="all"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info(f"Searching for '{query}' (Type: {search_type})")
    
    # 1. Search Monitors (default search)
    if search_type in ["all", "monitor"]:
        logger.info("Scanning Monitors...")
        response = client.list_monitors()
        if response and 'response' in response and 'result' in response['response']:
            monitors = response['response']['result']
            for monitor in monitors:
                host_ip = monitor.get('HOSTIP', '')
                host_name = monitor.get('HOSTNAME', '')
                display_name = monitor.get('DISPLAYNAME', '')
                
                # Check match
                if query in host_ip or query in host_name or query in display_name:
                    print(f"\n[MONITOR] {display_name} (ID: {monitor.get('RESOURCEID', 'N/A')})")
                    print(f"  Type: {monitor.get('TYPE', 'N/A')}")
                    print(f"  Host/IP: {host_name} / {host_ip}")
                    print(f"  Status: {monitor.get('HEALTHSTATUS', 'Unknown')}")
                    
    # 2. Search Groups (if monitor search didn't find specific things, or if requested)
    if search_type in ["all", "group"]:
        logger.info("Scanning Monitor Groups...")
        # Note: AppManager API for listing groups can be tricky. Using generic ListMonitor with type=HAI often works.
        try:
            # We can use the generic client request method to invoke ListMonitor with type=HAI
            params = {"type": "HAI"} # HAI = High Availability Interface? Often used for Groups
            response = client.request("ListMonitor", params=params)
            
            if response and 'response' in response and 'result' in response['response']:
                groups = response['response']['result']
                for group in groups:
                    display_name = group.get('DISPLAYNAME', '')
                    resource_id = group.get('RESOURCEID', '')
                    
                    if query.lower() in display_name.lower():
                        print(f"\n[GROUP] {display_name} (ID: {resource_id})")
                        print(f"  Type: {group.get('TYPE', 'Monitor Group')}")
                        print(f"  Health: {group.get('HEALTHSTATUS', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error scanning groups: {e}")

def main():
    parser = argparse.ArgumentParser(description="Find Resources in AppManager (Monitors or Groups)")
    parser.add_argument("query", help="Search term (IP, Name, or part of name)")
    parser.add_argument("--type", choices=["all", "monitor", "group"], default="all", help="Type of resource to search for")
    
    args = parser.parse_args()
    
    find_resource(args.query, args.type)

if __name__ == "__main__":
    main()
