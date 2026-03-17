import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def associate_ad_group(group_id="10113133", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml/AssociateMonitorToGroup"
    
    params = {
        "apikey": DEFAULT_API_KEY,
        "groupid": group_id,
        "resourceid": resource_id
    }
    
    print("--- Associating Resource " + resource_id + " to Group " + group_id + " ---")
    print("URL: " + base_url)
    
    try:
        res = requests.post(base_url, params=params, verify=False)
        
        print("\nHTTP Status: " + str(res.status_code))
        # Handle encoding issues by slicing text safely
        print("Response:\n" + res.text[:500])
        
        if "success" in res.text.lower() or "associated" in res.text.lower():
            print("\nSUCCESS! Monitor added to group.")
        else:
            print("\nWarning: Check response for details.")
            
    except Exception as e:
        print("Exception: " + str(e))

if __name__ == "__main__":
    associate_ad_group()