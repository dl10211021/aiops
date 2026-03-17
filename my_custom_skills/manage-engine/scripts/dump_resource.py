
import sys
import argparse
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import logging

logging.basicConfig(level=logging.INFO)

def main():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    res_id = sys.argv[1]
    
    print(f"Fetching details for {res_id}...")
    data = client.get_monitor_data(res_id)
    
    if data and 'response' in data and 'result' in data['response']:
        result = data['response']['result']
        if isinstance(result, list):
            result = result[0] # Take first if list
            
        print(f"Resource: {result.get('DISPLAYNAME')} ({result.get('TYPE')})")
        
        # Print Attributes
        # Structure varies, looking for key-value pairs or list of attributes
        # Sometimes it's a flat dict.
        for k, v in result.items():
            print(f"{k}: {v}")
            
    else:
        print("No data found.")
        print(data)

if __name__ == "__main__":
    main()
