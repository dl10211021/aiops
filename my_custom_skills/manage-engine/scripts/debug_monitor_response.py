import json
import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def debug_monitor(resource_id):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(resource_id)
    # Print the full JSON, but truncate long lists if necessary
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    resource_id = sys.argv[1] if len(sys.argv) > 1 else "10058525"
    debug_monitor(resource_id)
