from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def configure_combined_alarm(resource_id, action_ids):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    # Action IDs should be a comma-separated string for multiple actions
    # e.g., "10000012,10000013"
    
    print(f"Configuring Alarm for Resource {resource_id} with Actions: {action_ids}...")
    
    # 1. Configure Availability (700)
    print(">> Configuring Availability (700)...")
    resp1 = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="700",
        threshold_id="1", 
        critical_action_id=action_ids,
        clear_action_id=action_ids,
        availability_critical_poll_count=1,
        availability_clear_poll_count=1,
        request_type=1,
        override_conf=True
    )
    print("Response 700:", resp1)

    # 2. Configure Health (701)
    print(">> Configuring Health (701)...")
    resp2 = client.configure_alarm(
        resource_id=resource_id,
        attribute_id="701",
        threshold_id="1",
        critical_action_id=action_ids,
        clear_action_id=action_ids,
        request_type=1,
        override_conf=True
    )
    print("Response 701:", resp2)

if __name__ == "__main__":
    # Resource: Java_Process (10113666)
    # Actions: Ding Lu (10000012) + Test Robot (10000013)
    combined_actions = "10000012,10000013"
    configure_combined_alarm("10113666", combined_actions)