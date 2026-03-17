import time
import os
import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def monitor_live(resource_id, duration_minutes=5):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    interval = 30 
    
    print("Starting live dashboard for ID: " + resource_id)
    time.sleep(1)

    try:
        for i in range(10): # Run for 10 cycles for now
            data = client.get_monitor_data(resource_id)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            if data and 'response' in data and 'result' in data['response']:
                res = data['response']['result'][0]
                print("============================================================")
                print("      LINUX LIVE DASHBOARD | " + time.strftime('%H:%M:%S'))
                print("============================================================")
                print("Resource: " + str(res.get('DISPLAYNAME')))
                print("Status  : " + str(res.get('AVAILABILITYSTATUS')))
                print("Health  : " + str(res.get('HEALTHSTATUS')).upper())
                print("------------------------------------------------------------")
                
                cpu = res.get('CPUUTIL', 'Pending...')
                mem = res.get('MEMUTIL', 'Pending...')
                rsp = res.get('RESPONSETIME', 'Pending...')
                
                if cpu == "-1": cpu = "Polling..."
                if mem == "-1": mem = "Polling..."
                
                print("CPU Usage   : " + str(cpu) + " %")
                print("Memory Usage: " + str(mem) + " %")
                print("Response    : " + str(rsp) + " ms")
                print("============================================================")
                print("Refreshing every 30s. Press Ctrl+C to exit.")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "10113062"
    monitor_live(target)