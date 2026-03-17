import sys
import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def list_actions():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    response = client.request("ListActions")
    
    print(f"{'ID':<15} | {'Type':<15} | {'Name'}")
    print("-" * 80)
    
    if response and 'response' in response and 'result' in response['response']:
        result = response['response']['result']
        # The result is often a list of categories, each containing 'Action' list
        # Or a flat list depending on version. The previous debug output showed categories.
        
        # Based on previous debug output:
        # [ { "DisplayName": "Rest API Action", "Action": [...] }, ... ]
        
        for category in result:
            cat_name = category.get('DisplayName', 'Unknown')
            actions = category.get('Action', [])
            
            if actions:
                # print(f"--- {cat_name} ---")
                for action in actions:
                    a_id = action.get('ID', 'N/A')
                    a_name = action.get('NAME', 'N/A')
                    # Type isn't explicitly in the item, it's inferred from category
                    print(f"{a_id:<15} | {cat_name[:15]:<15} | {a_name}")
    else:
        print("Failed to list actions.")

if __name__ == "__main__":
    list_actions()