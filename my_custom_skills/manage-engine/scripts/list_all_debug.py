
from manage_engine_api import AppManagerClient

client = AppManagerClient()
try:
    response = client.list_monitors()
    
    if not response:
        print("No response from API.")
        exit()

    result = client._get_result_list(response) # Use the helper!
    print(f"Total monitors found: {len(result)}")
    
    found_count = 0
    for m in result:
        # Convert to string for easy search
        m_str = str(m)
        if "240" in m_str:
            print(f"MATCH: {m.get('DISPLAYNAME', 'NoName')} (ID: {m.get('RESOURCEID')})")
            print(f"       IP: {m.get('HOSTIP', 'N/A')}")
            found_count += 1
            
    if found_count == 0:
        print("No match found for '104.240'. Listing first 5 monitors for debug:")
        for m in result[:5]:
             print(f"  - {m.get('DISPLAYNAME')} ({m.get('HOSTIP')})")

except Exception as e:
    print(f"Error: {e}")
