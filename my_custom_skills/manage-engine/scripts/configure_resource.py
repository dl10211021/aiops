
import sys
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('config_resource')

def configure_resource(resource_id, config_type, profile_id, action_id=None):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    # Map friendly type to Attribute ID
    # These are defaults for Linux/Windows. might differ for DBs.
    type_map = {
        "cpu": "708",
        "mem": "685", # or 702
        "disk": "711", # or 761
        "ping": "700"  # Availability
    }
    
    attr_id = type_map.get(config_type.lower())
    if not attr_id:
        logger.error(f"Unknown config type: {config_type}. Supported: cpu, mem, disk, ping")
        return

    logger.info(f"--- Configuring {config_type.upper()} (Attr: {attr_id}) for {resource_id} ---")
    logger.info(f"Threshold Profile: {profile_id}")
    
    params = {
        "resource_id": resource_id,
        "attribute_id": attr_id,
        "threshold_id": profile_id,
        "override_conf": True
    }
    
    if action_id:
        logger.info(f"Associating Action: {action_id}")
        params["critical_action_id"] = action_id
        params["warning_action_id"] = action_id
        params["clear_action_id"] = action_id
    
    response = client.configure_alarm(**params)
    logger.info(f"Response: {response}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure Monitor Thresholds & Actions")
    parser.add_argument("id", help="Resource ID")
    parser.add_argument("type", help="Type: cpu, mem, disk, ping")
    parser.add_argument("profile", help="Threshold Profile ID")
    parser.add_argument("--action", help="Action ID (Optional)", default=None)
    
    args = parser.parse_args()
    
    configure_resource(args.id, args.type, args.profile, args.action)
