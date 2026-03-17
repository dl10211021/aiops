import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY, Attributes

def configure_process_alarm(resource_id, action_id, consecutive_polls=1):
    """
    Configures availability alarm for a process monitor.
    Uses Attribute ID 715 (Process Availability).
    """
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"Configuring Process Availability (Attr {Attributes.PROCESS_AVAILABILITY}) for Resource {resource_id}...")
    print(f"Action ID: {action_id}")
    print(f"Consecutive Polls: {consecutive_polls}")
    
    response = client.configure_alarm(
        resource_id=resource_id,
        attribute_id=Attributes.PROCESS_AVAILABILITY,
        critical_action_id=action_id,
        clear_action_id=action_id,
        availability_critical_poll_count=consecutive_polls,
        availability_clear_poll_count=consecutive_polls,
        request_type=1, # Save
        override_conf=True
    )
    
    print(f"Response: {response}")
    return response

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure Availability Alarm for Process Monitor")
    parser.add_argument("resource_id", help="Resource ID of the process monitor")
    parser.add_argument("action_id", help="Action ID (e.g., Email or WeChat Robot)")
    parser.add_argument("--polls", type=int, default=1, help="Consecutive polls before alarm (default: 1)")
    
    args = parser.parse_args()
    
    configure_process_alarm(args.resource_id, args.action_id, args.polls)
