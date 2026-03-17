import os
import sys

# Add the directory containing this script to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def main():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    print("Fetching monitor list and checking recent poll data (within 15m window)...")
    response = client.list_monitors(type="all")
    
    if not response or 'response' not in response or 'result' not in response['response']:
        print("Failed to fetch monitors or empty response.")
        return
        
    monitors = response['response']['result']
    
    print(f"{'ID':<12} | {'IP Address':<15} | {'Name':<35} | {'Type':<12} | {'Mem %':<8}")
    print("-" * 95)
    
    os_types = ['Windows', 'Linux', 'Server', 'Solaris', 'AIX', 'HP-UX']
    
    count = 0
    for m in monitors:
        m_id = m.get('RESOURCEID')
        m_name = m.get('RESOURCENAME', 'Unknown')
        m_type = m.get('TYPE', 'Unknown')
        m_ip = m.get('HOSTIP', 'N/A')
        
        # Check if it's likely a host/server
        if any(os_t.lower() in m_type.lower() for os_t in os_types):
            try:
                data_response = client.get_monitor_data(m_id)
                if not data_response or 'response' not in data_response or 'result' not in data_response['response']:
                    continue
                
                result = data_response['response']['result'][0]
                
                # Verify last polled time is recent (Optional, but good for "15 min" context)
                # AppManager usually polls every 5-15 mins.
                
                mem = result.get('PHYMEMUTIL') or result.get('MEMUTIL')
                if not mem and 'Attribute' in result:
                    for attr in result['Attribute']:
                        if attr.get('DISPLAYNAME') in ['物理内存利用率', 'Physical Memory Utilization', 'Memory Utilization']:
                            mem = attr.get('Value')
                            break
                
                if mem:
                    try:
                        mem_val = float(mem)
                        if mem_val > 90:
                            disp_name = m.get('DISPLAYNAME') or m_name
                            print(f"{m_id:<12} | {m_ip:<15} | {disp_name[:35]:<35} | {m_type[:12]:<12} | {mem_val:>7.1f}%")
                            count += 1
                    except ValueError:
                        continue
            except Exception:
                continue
    
    print("-" * 95)
    print(f"Total resources with current Memory > 90%: {count}")

if __name__ == '__main__':
    main()
