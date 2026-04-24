import sys
import json
import logging
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AppManager_Inspector')

def inspect_alarms(client):
    logger.info("Checking for active alarms...")
    alarms = client.list_alarms(type="critical")
    
    if alarms and 'response' in alarms and 'result' in alarms['response']:
        results = alarms['response']['result']
        critical_count = len(results)
        logger.warning(f"Found {critical_count} critical alarms in the system!")
        
        # Debug: Print raw data of the first alarm to identify correct keys
        if critical_count > 0:
            print("\n--- DEBUG: First Alarm Raw Data ---")
            print(json.dumps(results[0], indent=2))
            print("-----------------------------------\n")

        print("\n=== Critical Alarms Detail ===")
        print(f"{'Source':<30} | {'Message':<50} | {'Time':<20}")
        print("-" * 105)
        
        for alarm in results:
            # AppManager API uses uppercase keys in some versions
            source = alarm.get('DISPLAYNAME', alarm.get('displayname', 'Unknown Source'))
            message = alarm.get('MESSAGE', alarm.get('message', 'No message'))
            time = alarm.get('FORMATTEDDATE', alarm.get('modtime', 'Unknown Time'))
            
            # Simple HTML tag removal for better CLI display
            import re
            clean_message = re.sub('<[^<]+?>', '', str(message))
            
            print(f"{str(source)[:30]:<30} | {str(clean_message)[:50]:<50} | {str(time):<20}")
        print("-" * 105)
    else:
        logger.info("No critical alarms found.")

def run_daily_inspection(resource_id="10030298"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info(f"Starting inspection for Resource ID: {resource_id}")
    
    # 1. Check Alarms
    inspect_alarms(client)

    # 2. Check Specific Resource Status
    logger.info(f"Fetching health status for {resource_id}...")
    data = client.get_monitor_data(resource_id)
    
    if data and 'response' in data and 'result' in data['response']:
        # AppManager JSON structure can be complex, usually it's a list under 'result'
        metrics = data['response']['result']
        logger.info(f"Successfully retrieved metrics for {resource_id}.")
        # Here you could add logic to check specific metric thresholds
        # print(json.dumps(metrics, indent=2))
    else:
        logger.error(f"Could not retrieve data for resource {resource_id}. Check if ID is correct and API key is valid.")

if __name__ == "__main__":
    target_id = sys.argv[1] if len(sys.argv) > 1 else "10030298"
    run_daily_inspection(target_id)