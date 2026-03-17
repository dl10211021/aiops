import time
import sys
import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Configuration
RESOURCE_ID = "10113344" # From previous run
ACTION_ID = "10000012"
CPU_THRESHOLD_ID = "10000092"
MEM_THRESHOLD_ID = "10000093"
DISK_THRESHOLD_ID = "10000087"

ATTR_CPU = "708"
ATTR_MEM = "709"
ATTR_DISK = "711"

def retry_config():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    print(f"--- Retrying Configuration for Resource {RESOURCE_ID} ---")

    # 1. Thresholds
    print("Configuring Thresholds...")
    try:
        # Try AssociateThresholdProfile (XML)
        client.associate_threshold_profile(RESOURCE_ID, ATTR_CPU, CPU_THRESHOLD_ID)
        print(" -> CPU Threshold Set")
        client.associate_threshold_profile(RESOURCE_ID, ATTR_MEM, MEM_THRESHOLD_ID)
        print(" -> Memory Threshold Set")
        client.associate_threshold_profile(RESOURCE_ID, ATTR_DISK, DISK_THRESHOLD_ID)
        print(" -> Disk Threshold Set")
    except Exception as e:
        print(f" -> Threshold Error: {e}")

    # 2. Actions
    print("Configuring Actions...")
    try:
        # Try AssociateActionToAttribute (JSON) - Maybe URL is /AppManager/xml/AssociateActionToAttribute?
        # Let's try forcing XML if JSON fails, or check common endpoints
        
        # CPU
        res = client.request("AssociateActionToAttribute", params={
            "resourceid": RESOURCE_ID,
            "attributeid": ATTR_CPU,
            "criticalactionid": ACTION_ID,
            "warningactionid": ACTION_ID
        })
        print(f" -> CPU Action Associated (Response: {res})")

        # Memory
        res = client.request("AssociateActionToAttribute", params={
            "resourceid": RESOURCE_ID,
            "attributeid": ATTR_MEM,
            "criticalactionid": ACTION_ID,
            "warningactionid": ACTION_ID
        })
        print(f" -> Memory Action Associated")
        
        # Availability
        res = client.request("AssociateActionToAttribute", params={
            "resourceid": RESOURCE_ID,
            "attributeid": "17", 
            "criticalactionid": ACTION_ID
        })
        print(f" -> Availability Action Associated")

    except Exception as e:
        print(f" -> Action Error: {e}")

if __name__ == "__main__":
    retry_config()