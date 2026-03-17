import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def associate_variant_params(group_id="10113133", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml/AssociateMonitorToGroup"
    
    combinations = [
        {"name": "Standard (groupid)", "p": {"groupid": group_id, "resourceid": resource_id}},
        {"name": "Legacy (haid)",     "p": {"haid": group_id,    "resourceid": resource_id}}
    ]
    
    print("--- Testing AssociateMonitorToGroup Permutations ---")
    print("URL: " + base_url)
    
    for combo in combinations:
        params = combo["p"]
        params["apikey"] = DEFAULT_API_KEY
        
        print("\nTrying: " + combo["name"])
        try:
            res = requests.post(base_url, params=params, verify=False)
            print("HTTP Status: " + str(res.status_code))
            
            if res.status_code != 404:
                print("Response:\n" + res.text[:300])
                if "success" in res.text.lower():
                    print("SUCCESS!")
                    return
            else:
                print("Response: 404 Not Found")
                
        except Exception as e:
            print("Exception: " + str(e))

if __name__ == "__main__":
    associate_variant_params()