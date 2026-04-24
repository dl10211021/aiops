from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def main():
    target_ip = "192.168.130.45"
    target_id = "10113062"
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- 1. Setting up 'test' Group for " + target_ip + " ---")
    
    # List all monitors
    print("Fetching all monitors...")
    all_monitors = client.list_monitors()
    test_group_id = None
    
    if all_monitors and 'response' in all_monitors and 'result' in all_monitors['response']:
        for m in all_monitors['response']['result']:
            if m.get('DISPLAYNAME') == 'test' and 'Group' in m.get('TYPE', ''):
                test_group_id = m.get('RESOURCEID')
                print("Found 'test' group: " + str(test_group_id))
                break
    
    if not test_group_id:
        print("Creating 'test' group...")
        res = client.create_monitor_group("test")
        # Check if creation succeeded
        if res and 'response' in res and 'result' in res['response']:
            test_group_id = res['response']['result'][0].get('RESOURCEID')
            print("Created group ID: " + str(test_group_id))
        else:
            print("Could not verify group creation.")

    if test_group_id:
        print("Associating monitor " + target_id + " to group " + str(test_group_id))
        # Important: API param is often 'resourceid' with comma separated values
        client.associate_monitor_to_group(test_group_id, [target_id])
    
    print("\n--- 2. Applying Standard Alarm Profile (>90% Critical) ---")
    
    # Since ListThresholdProfiles is 404, we assume ID 1 (Standard Profile) exists.
    profile_id = "1"
    attr_id = "708" # CPU Utilization
    
    print("Associating Profile ID " + profile_id + " to Attribute " + attr_id + "...")
    try:
        res = client.associate_threshold_profile(target_id, attr_id, profile_id)
        print("Result: " + str(res))
    except Exception as e:
        print("Failed to associate: " + str(e))

if __name__ == "__main__":
    main()