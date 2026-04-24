import argparse
import xml.etree.ElementTree as ET
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY, Attributes

def add_process(resource_id, process_name, display_name=None, action_id=None):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"Adding process '{process_name}' to resource {resource_id}...")
    params = {
        "resourceid": resource_id,
        "name": process_name
    }
    if display_name:
        params["displayname"] = display_name
    
    # Add Process
    response_xml = client.request("process/add", params=params, method="POST", format="xml")
    print(f"Add Response: {response_xml}")
    
    # If action_id provided, parse response to find new resource ID and configure alarm
    if action_id and response_xml:
        try:
            root = ET.fromstring(response_xml)
            # Typically <response resourceid="10113682" response-code="4000">
            response_elem = root.find(".//response")
            if response_elem is not None:
                new_resource_id = response_elem.get("resourceid")
                response_code = response_elem.get("response-code")
                
                if response_code == "4000" and new_resource_id:
                    print(f"Process added successfully with ID: {new_resource_id}")
                    configure_process_alarm(client, new_resource_id, action_id)
                else:
                    print("Could not verify success or find new resource ID to configure alarm.")
        except Exception as e:
            print(f"Error parsing response to configure alarm: {e}")

    return response_xml

def configure_process_alarm(client, resource_id, action_id):
    print(f"Configuring Process Availability (Attr {Attributes.PROCESS_AVAILABILITY}) for {resource_id}...")
    
    response = client.configure_alarm(
        resource_id=resource_id,
        attribute_id=Attributes.PROCESS_AVAILABILITY,
        critical_action_id=action_id,
        clear_action_id=action_id,
        availability_critical_poll_count=1,
        availability_clear_poll_count=1,
        request_type=1,
        override_conf=True
    )
    print(f"Alarm Configuration Response: {response}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a process monitor to a server.")
    parser.add_argument("resource_id", help="ID of the parent server resource")
    parser.add_argument("process_name", help="Name of the process (e.g., java.exe)")
    parser.add_argument("--name", help="Display Name for the monitor", default=None)
    parser.add_argument("--action", help="Action ID to associate for availability alerts", default=None)
    
    args = parser.parse_args()
    
    add_process(args.resource_id, args.process_name, args.name, args.action)
