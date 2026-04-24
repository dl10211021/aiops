import json
import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Ensure UTF-8 output for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_sample():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("Listing monitors...")
    monitors_resp = client.list_monitors()
    
    if not monitors_resp or 'response' not in monitors_resp:
        print("Failed to list monitors")
        return

    monitors = monitors_resp['response']['result']
    target_id = None
    target_name = None
    
    # Find a Critical monitor
    for m in monitors:
        if m.get('HEALTHSTATUS') == 'critical':
            target_id = m.get('RESOURCEID')
            target_name = m.get('DISPLAYNAME')
            print(f"Found Critical target: {target_name} ({target_id}) Type: {m.get('TYPE')}")
            break
            
    if not target_id:
        print("No Critical monitor found. Trying Warning...")
        for m in monitors:
            if m.get('HEALTHSTATUS') == 'warning':
                target_id = m.get('RESOURCEID')
                target_name = m.get('DISPLAYNAME')
                print(f"Found Warning target: {target_name} ({target_id}) Type: {m.get('TYPE')}")
                break
    
    if not target_id:
        print("No Critical or Warning monitors found.")
        return

    print(f"\nFetching details for {target_id}...")
    data = client.get_monitor_data(target_id)
    
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("Failed to fetch monitor data.")

if __name__ == "__main__":
    check_sample()
