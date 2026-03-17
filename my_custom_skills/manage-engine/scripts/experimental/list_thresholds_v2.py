import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def list_thresholds_v2_fixed():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    print("Fetching threshold profiles...")
    
    endpoint = "threshold"
    try:
        data = client.request(endpoint, format="json")
    except Exception as e:
        print(f"Error: {e}")
        return

    if not data or 'response' not in data:
        print("Invalid response from API.")
        return

    # AppManager often nests the list inside another 'response' or directly under 'result'
    # Based on docs: <result><response><Threshold .../></response></result>
    
    try:
        result_node = data['response']['result']
        # The documentation sample shows result -> response -> Threshold
        # But JSON format might be different. Let's find 'Threshold' list.
        
        thresholds = []
        if isinstance(result_node, dict):
            if 'response' in result_node and 'Threshold' in result_node['response']:
                thresholds = result_node['response']['Threshold']
            elif 'Threshold' in result_node:
                thresholds = result_node['Threshold']
        
        if not thresholds:
             # Fallback: search deep in the dict
             def find_key(d, key):
                 if key in d: return d[key]
                 for k, v in d.items():
                     if isinstance(v, dict):
                         item = find_key(v, key)
                         if item: return item
                 return None
             thresholds = find_key(data, 'Threshold')

        if not thresholds:
            print("No thresholds found in the JSON response.")
            print(json.dumps(data, indent=2))
            return

        if isinstance(thresholds, dict): # Single item
            thresholds = [thresholds]

        print(f"Found {len(thresholds)} thresholds.")
        print("-" * 80)
        for t in thresholds:
            tid = t.get('THRESHOLDID', 'N/A')
            name = t.get('THRESHOLDNAME', 'N/A')
            c_val = t.get('CRITICALTHRESHOLDVALUE', '-')
            w_val = t.get('WARNINGTHRESHOLDVALUE', '-')
            c_cond = t.get('CRITICALTHRESHOLDCONDITION', '-')
            
            print(f"ID: {tid} | Name: {name}")
            print(f"  Critical: {c_cond} {c_val} | Warning: {w_val}")
            desc = t.get('DESCRIPTION')
            if desc: print(f"  Desc: {desc}")
            print("-" * 40)

    except Exception as e:
        print(f"Processing error: {e}")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    list_thresholds_v2_fixed()