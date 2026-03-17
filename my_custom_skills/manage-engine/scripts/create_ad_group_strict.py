import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_ad_group_strict():
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml/AddMonitorGroup"
    
    # Strict parameters based on documentation
    params = {
        "apikey": DEFAULT_API_KEY,
        "grouptype": "monitorgroup",
        "name": "ADTest"  # Using ASCII to avoid encoding issues initially
    }
    
    print("--- Creating Group: 'ADTest' (Strict Mode) ---")
    print("URL: " + base_url)
    
    try:
        res = requests.post(base_url, params=params, verify=False)
        
        print("\nHTTP Status: " + str(res.status_code))
        print("Response:\n" + res.text[:500])
        
        if res.status_code == 200 and "resourceid" in res.text:
            print("\nSUCCESS! Group Created/Found.")
        elif res.status_code == 403:
            print("\nFORBIDDEN (403).")
            print("Reason: Documentation requires 'Administrator' role.")
            print("Conclusion: Your API Key lacks permissions.")
        elif "4008" in res.text:
            print("\nParameter Error (4008).")
            
    except Exception as e:
        print("Exception: " + str(e))

if __name__ == "__main__":
    create_ad_group_strict()