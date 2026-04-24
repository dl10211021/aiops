from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def inspect_resources():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- 1. Searching for 'test' Group ---")
    groups = client.list_monitors(type="Monitor Group")
    test_group_id = None
    if groups and 'response' in groups and 'result' in groups['response']:
        for g in groups['response']['result']:
            if g.get('DISPLAYNAME') == 'test':
                test_group_id = g.get('RESOURCEID')
                print(f"Found Group: test (ID: {test_group_id})")
                break
    if not test_group_id:
        print("Group 'test' not found.")

    print("\n--- 2. Searching for Actions (DingLu) ---")
    try:
        actions_xml = client.request("ListActions", format="xml")
        if actions_xml:
            # Simple string search for ID
            if "丁露" in actions_xml:
                print("Found '丁露' in actions.")
                # Try to parse ID using basic parsing or regex if XML lib fails
                # Let's try to print the line containing it
                for line in actions_xml.split('\n'):
                    if "丁露" in line:
                        print(f"Relevant line: {line.strip()}")
            else:
                print("Could not find '丁露' in action list.")
    except Exception as e:
        print(f"Error fetching actions: {e}")

    print("\n--- 3. Listing Threshold Profiles ---")
    try:
        data = client.request("threshold", format="json")
        if data and 'response' in data and 'result' in data['response']:
            ts_list = data['response']['result']
            if isinstance(ts_list, dict): ts_list = [ts_list]
            
            print(f"Found {len(ts_list)} profiles.")
            for t in ts_list:
                name = t.get('THRESHOLDNAME', '')
                if "CPU" in name or "Disk" in name or "Memory" in name or "磁盘" in name or "内存" in name:
                    print(f" - {name} (ID: {t.get('THRESHOLDID')})")
    except Exception as e:
        print(f"Error fetching thresholds: {e}")

if __name__ == "__main__":
    inspect_resources()