from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def get_full_linux_stats(resource_id="10113062"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(resource_id)
    
    if data and 'response' in data and 'result' in data['response']:
        res = data['response']['result'][0]
        
        print("\n--- Full Metrics for ID: " + resource_id + " ---")
        print("[ CORE USAGE ]")
        print(" > CPU: " + str(res.get('CPUUTIL', 'N/A')) + "%")
        print(" > MEM: " + str(res.get('MEMUTIL', 'N/A')) + "%")
        
        print("\n[ DISK & NETWORK DETAILS ]")
        found = False
        for k, v in res.items():
            if any(p in k.lower() for p in ['disk', 'network', 'interface', 'eth', 'swap', 'partition']):
                if v and v != "-1":
                    print(" > " + k + ": " + str(v))
                    found = True
        if not found:
            print(" ! No detailed sub-metrics returned in this view.")
    else:
        print("Error fetching data.")

if __name__ == "__main__":
    get_full_linux_stats()