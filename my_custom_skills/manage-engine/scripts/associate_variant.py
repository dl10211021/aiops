import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def try_add_monitor_variant(group_id="10113133", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml/AddMonitor"
    
    params = {
        "apikey": DEFAULT_API_KEY,
        "type": "MonitorGroup", 
        "groupid": group_id, 
        "resourceid": resource_id 
    }
    
    print("--- Attempting Association via AddMonitor ---")
    print("URL: " + base_url)
    
    try:
        res = requests.post(base_url, params=params, verify=False)
        
        print("\nHTTP Status: " + str(res.status_code))
        # Handle encoding
        print("Response:\n" + res.text[:500])
        
        if "success" in res.text.lower() or "associated" in res.text.lower() or "added" in res.text.lower():
             print("\nSUCCESS! Monitor associated via AddMonitor.")
        elif "4008" in res.text:
             print("\nParameter Error (4008).")
             
    except Exception as e:
        print("Exception: " + str(e))

if __name__ == "__main__":
    try_add_monitor_variant()