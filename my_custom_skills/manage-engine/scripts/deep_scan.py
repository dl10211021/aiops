import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def deep_scan_attributes(resource_id="10113062"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(resource_id)
    
    if data and 'response' in data and 'result' in data['response']:
        res = data['response']['result'][0]
        print("\n--- Scanning fields for ID: " + resource_id + " ---")
        potential_metrics = []
        for k, v in res.items():
            if v and v != "-1" and v != "NA":
                potential_metrics.append((k, v))
        for k, v in potential_metrics:
            print(k + ": " + str(v))

if __name__ == "__main__":

    deep_scan_attributes("10058525")
