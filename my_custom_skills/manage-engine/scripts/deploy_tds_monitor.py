import time
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Configuration
TARGET_IP = "192.168.130.45"
DISPLAY_NAME = "TDS_192.168.130.45"
USER = "root"
PASS = "cnChervon@123"
GROUP_NAME = "test"
ACTION_ID = "10000012"  # DingLu WeChat Robot

# Threshold Profile IDs
CPU_THRESHOLD_ID = "10000092"   # CPU > 80%
MEM_THRESHOLD_ID = "10000093"   # Mem > 80%
DISK_THRESHOLD_ID = "10000087"  # Disk > 70%

# Attribute IDs for Linux
ATTR_CPU = "708"
ATTR_MEM = "709"
ATTR_DISK = "711" 

def deploy_monitor():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    print("--- Deploying Monitor: " + DISPLAY_NAME + " ---")

    # 1. Get or Create Group
    print("\n[1/4] Ensuring Group '" + GROUP_NAME + "' exists...")
    group_id = None
    
    # List all groups first
    try:
        # Try both monitor group type and generic to be sure
        groups = client.list_monitors(type="Monitor Group")
        if groups and 'response' in groups and 'result' in groups['response']:
            for g in groups['response']['result']:
                # Flexible matching (case insensitive)
                if g.get('DISPLAYNAME', '').lower() == GROUP_NAME.lower():
                    group_id = str(g.get('RESOURCEID'))
                    print(" -> Found existing group ID: " + group_id)
                    break
    except Exception as e:
        print(" -> Warning during group search: " + str(e))

    # If not found, create it
    if not group_id:
        print(" -> Group not found. Attempting creation via API...")
        try:
            # Note: create_monitor_group in api lib uses /xml/AddMonitorGroup
            # Ensure parameters are correct.
            res = client.create_monitor_group(GROUP_NAME)
            print(" -> Create command sent. Response: " + str(res)[:100] + "...")
            
            # Wait and re-check
            time.sleep(3)
            groups = client.list_monitors(type="Monitor Group")
            if groups and 'response' in groups and 'result' in groups['response']:
                for g in groups['response']['result']:
                    if g.get('DISPLAYNAME', '').lower() == GROUP_NAME.lower():
                        group_id = str(g.get('RESOURCEID'))
                        print(" -> Created group ID: " + group_id)
                        break
        except Exception as e:
            print(" -> Error creating group: " + str(e))

    if not group_id:
        print(" ! Warning: Could not resolve group ID. Monitor will be added to Default group.")
    
    # 2. Add Monitor
    print("\n[2/4] Adding Linux Monitor...")
    existing_id = None
    
    # Check if monitor already exists
    try:
        monitors = client.list_monitors(type="Linux")
        if monitors and 'response' in monitors and 'result' in monitors['response']:
            for m in monitors['response']['result']:
                if m.get('DISPLAYNAME') == DISPLAY_NAME or m.get('IPADDRESS') == TARGET_IP:
                    existing_id = str(m.get('RESOURCEID'))
                    print(" -> Monitor already exists (ID: " + existing_id + "). Updating configuration...")
                    break
    except Exception as e:
        print(" -> Error checking monitors: " + str(e))
    
    if not existing_id:
        try:
            # Add Monitor with Group ID if available
            print(" -> Adding monitor " + TARGET_IP + " to group " + str(group_id))
            add_res = client.add_linux_monitor(TARGET_IP, USER, PASS, display_name=DISPLAY_NAME, group_id=group_id)
            print(" -> Add command sent.")
            
            # Wait for initialization
            print(" -> Waiting 10s for initialization...")
            time.sleep(10)
            
            # Fetch ID
            monitors = client.list_monitors(type="Linux")
            if monitors and 'response' in monitors and 'result' in monitors['response']:
                for m in monitors['response']['result']:
                    if m.get('DISPLAYNAME') == DISPLAY_NAME:
                        existing_id = str(m.get('RESOURCEID'))
                        break
        except Exception as e:
            print(" -> Error adding monitor: " + str(e))
    
    if not existing_id:
        print("Error: Could not retrieve new Monitor ID. It might be initializing or failed.")
        return
    
    print(" -> Target Monitor ID: " + existing_id)

    # 3. Configure Thresholds
    print("\n[3/4] Configuring Thresholds...")
    try:
        print(" -> Setting CPU Threshold (ID " + CPU_THRESHOLD_ID + ")...")
        client.associate_threshold_profile(existing_id, ATTR_CPU, CPU_THRESHOLD_ID)
        
        print(" -> Setting Memory Threshold (ID " + MEM_THRESHOLD_ID + ")...")
        client.associate_threshold_profile(existing_id, ATTR_MEM, MEM_THRESHOLD_ID)
        
        print(" -> Setting Disk Threshold (ID " + DISK_THRESHOLD_ID + ")...")
        client.associate_threshold_profile(existing_id, ATTR_DISK, DISK_THRESHOLD_ID)
    except Exception as e:
        print(" -> Error configuring thresholds: " + str(e))

    # 4. Associate Action
    print("\n[4/4] Associating Action: DingLu WeChat Robot (ID " + ACTION_ID + ")...")
    try:
        # Associate to CPU
        client.request("AssociateActionToAttribute", params={
            "resourceid": existing_id,
            "attributeid": ATTR_CPU,
            "criticalactionid": ACTION_ID,
            "warningactionid": ACTION_ID
        })
        print(" -> Associated to CPU")

        # Associate to Memory
        client.request("AssociateActionToAttribute", params={
            "resourceid": existing_id,
            "attributeid": ATTR_MEM,
            "criticalactionid": ACTION_ID,
            "warningactionid": ACTION_ID
        })
        print(" -> Associated to Memory")
        
        # Associate to Availability (Down)
        client.request("AssociateActionToAttribute", params={
            "resourceid": existing_id,
            "attributeid": "17", 
            "criticalactionid": ACTION_ID
        })
        print(" -> Associated to Availability (Down)")
    except Exception as e:
        print(" -> Error associating actions: " + str(e))

    print("\n--- Deployment Complete ---")
    print("Monitor '" + DISPLAY_NAME + "' is active.")

if __name__ == "__main__":
    deploy_monitor()