import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def dump_monitor_data(target_id):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(target_id)
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    dump_monitor_data("10074136")