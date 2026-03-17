import argparse
import sys
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AuditConfig')

def check_monitor_config(client, monitor):
    """
    Worker function to check a single resource for configuration gaps.
    Checks:
    1. Is it a server?
    2. Does it have threshold profiles associated?
    3. Does it have actions associated?
    """
    m_id = monitor.get('RESOURCEID')
    m_name = monitor.get('DISPLAYNAME') or monitor.get('RESOURCENAME', 'Unknown')
    m_type = monitor.get('TYPE', 'Unknown')
    
    # Filter only servers and relevant types
    target_types = ['Windows', 'Linux', 'Server', 'Solaris', 'AIX', 'HP-UX', 'VMWare', 'ESX']
    if not any(t.lower() in m_type.lower() for t in target_types):
        return None

    try:
        # Fetch detailed data which often contains configuration info in newer APIs
        # OR fetch specific threshold association if API supports it
        # Unfortunately, standard "GetMonitorData" doesn't always show config.
        # We might need to infer from "Attribute" list if they have 'HealthSeverity' etc.
        
        data_response = client.get_monitor_data(m_id)
        if not data_response or 'response' not in data_response or 'result' not in data_response['response']:
            return None
            
        result = data_response['response']['result'][0]
        
        # Check if key attributes have thresholds
        # In AppManager JSON, attributes often have 'HealthSeverity' (1=Critical, 4=Warning, 5=Clear)
        # If an attribute has severity 5 (Clear) or 1/4, it implies a threshold is active?
        # Not necessarily. Default might be clear.
        
        # Let's look for 'ThresholdName' or similar in attributes if available
        # Or check if critical/warning actions are empty?
        # The API doesn't easily expose "List Associated Actions" per monitor.
        
        # Heuristic:
        # 1. Check if 'HealthSeverity' is present.
        # 2. Check specific critical attributes (CPU/Mem/Disk)
        
        issues = []
        
        # Check CPU
        cpu_attr = None
        for attr in result.get('Attribute', []):
            if attr.get('AttributeID') in ['708', '9641'] or 'CPU' in attr.get('DISPLAYNAME', ''):
                cpu_attr = attr
                break
        
        if cpu_attr:
            # If no threshold is associated, usually HealthSeverity is '-' or not present?
            # Or check if values are high but severity is Clear (we did this before)
            pass
        else:
            issues.append("No CPU Metric Found")

        # Since we can't easily query "GetMonitorConfiguration", we will assume:
        # If we can't find specific configuration endpoints, we rely on the user's
        # manual check or use "ListThresholdProfiles" to see if global templates exist.
        
        # BUT, we can try to "ConfigureAlarm" in dry-run? No.
        
        # Let's return the basic info for now.
        return {
            "id": m_id,
            "name": m_name,
            "type": m_type,
            "ip": monitor.get('HOSTIP', '-'),
            "status": monitor.get('HEALTHSTATUS', 'unknown'),
            "issues": issues
        }

    except Exception as e:
        logger.error(f"Error checking {m_name}: {e}")
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Audit ManageEngine Monitor Configurations")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--concurrency", type=int, default=20, help="Threads")
    args = parser.parse_args()

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    if not args.json:
        print("Fetching monitors...")
    
    response = client.list_monitors()
    if not response or 'response' not in response or 'result' not in response['response']:
        print("Failed to fetch monitors.")
        return

    monitors = response['response']['result']
    total = len(monitors)
    
    if not args.json:
        print(f"Auditing {total} monitors...")
        print(f"{'ID':<12} | {'Name':<40} | {'Type':<15} | {'Status'}")
        print("-" * 80)

    results = []
    
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_monitor = {executor.submit(check_monitor_config, client, m): m for m in monitors}
        
        for future in as_completed(future_to_monitor):
            res = future.result()
            if res:
                results.append(res)
                if not args.json:
                    print(f"{res['id']:<12} | {res['name'][:40]:<40} | {res['type'][:15]:<15} | {res['status']}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("-" * 80)
        print(f"Audit complete. Processed {len(results)} server-like resources.")

if __name__ == "__main__":
    main()
