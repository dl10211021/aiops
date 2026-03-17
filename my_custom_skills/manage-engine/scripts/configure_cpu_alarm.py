import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def main():
    target_ip = "192.168.130.45"
    target_id = "10113062"
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- 1. Setting up 'test' Group ---")
    
    # List groups
    groups = client.list_monitors(monitor_type="Monitor Group")
    test_group_id = None
    
    # Check existing
    if groups and 'response' in groups and 'result' in groups['response']:
        for g in groups['response']['result']:
            if g.get('DISPLAYNAME') == 'test':
                test_group_id = g.get('RESOURCEID')
                print("Found existing 'test' group: " + str(test_group_id))
                break
    
    # Create if not exists
    if not test_group_id:
        print("Creating 'test' group...")
        res = client.create_monitor_group("test", description="API Created")
        # Assuming creation returns the new ID or we re-list
        # API create usually returns result object
        if res and 'response' in res and 'result' in res['response']:
             test_group_id = res['response']['result'][0].get('RESOURCEID')
        
        if not test_group_id:
             print(" ! Could not auto-detect new group ID. Please create manually in UI.")
    
    # Associate
    if test_group_id:
        print("Associating " + target_ip + " to group " + str(test_group_id))
        client.associate_monitor_to_group(test_group_id, [target_id])
    
    print("\n--- 2. Setting up CPU > 80% Alarm ---")
    
    # List Threshold Profiles
    profiles = client.list_threshold_profiles()
    
    target_profile_id = None
    
    if profiles and 'response' in profiles and 'result' in profiles['response']:
        print("Available Profiles:")
        for p in profiles['response']['result']:
            p_name = p.get('DISPLAYNAME', 'Unknown')
            p_id = p.get('THRESHOLDID', '0')
            print(" - [" + str(p_id) + "] " + p_name)
            
            if "80" in p_name and "CPU" in p_name:
                target_profile_id = p_id
            elif "Critical" in p_name and "80" in p_name and not target_profile_id:
                target_profile_id = p_id

    # Fallback: Just pick the first one if not found (usually 'Standard')
    if not target_profile_id and profiles and 'response' in profiles and 'result' in profiles['response']:
        target_profile_id = profiles['response']['result'][0]['THRESHOLDID']
        print(" ! No specific '80%' profile found. Using default ID: " + str(target_profile_id))

    if target_profile_id:
        # Associate to CPU Utilization Attribute (708)
        print("Associating Profile " + str(target_profile_id) + " to CPU Attribute (708)...")
        res = client.associate_threshold_profile(target_id, "708", target_profile_id)
        # Also associate to Health (701) just in case
        print("Associating Profile " + str(target_profile_id) + " to Health Attribute (701)...")
        client.associate_threshold_profile(target_id, "701", target_profile_id)
        print("Done.")
    else:
        print("Error: No profiles available.")

if __name__ == "__main__":
    main()