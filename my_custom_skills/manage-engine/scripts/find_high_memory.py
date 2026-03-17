import os
import sys

# Add the directory containing this script to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def main():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    print("Fetching monitor list...")
    response = client.list_monitors(type="all")
    
    if not response or 'response' not in response or 'result' not in response['response']:
        print("Failed to fetch monitors or empty response.")
        return
        
    monitors = response['response']['result']
    
    print(f"{'ID':<12} | {'Name':<40} | {'Type':<15} | {'Memory %':<8}")
    print("-" * 85)
    
    # Target OS types
    os_types = ['Windows', 'Linux', 'Windows 2016', 'Windows 2019', 'Windows 2022']
    
    count = 0
    for m in monitors:
        m_id = m.get('RESOURCEID')
        m_name = m.get('RESOURCENAME', 'Unknown')
        m_type = m.get('TYPE', 'Unknown')
        
        if any(os_t in m_type for os_t in os_types):
            try:
                data_response = client.get_monitor_data(m_id)
                if not data_response or 'response' not in data_response or 'result' not in data_response['response']:
                    continue
                
                result = data_response['response']['result'][0]
                # Try direct fields first
                mem = result.get('PHYMEMUTIL') or result.get('MEMUTIL')
                
                # If not found, look in Attributes
                if not mem and 'Attribute' in result:
                    for attr in result['Attribute']:
                        if attr.get('DISPLAYNAME') in ['物理内存利用率', 'Physical Memory Utilization', 'Memory Utilization']:
                            mem = attr.get('Value')
                            break
                
                if mem:
                    try:
                        mem_val = float(mem)
                        if mem_val > 90:
                            # Use DisplayName from monitor list if available
                            disp_name = m.get('DISPLAYNAME') or m_name
                            print(f"{m_id:<12} | {disp_name[:40]:<40} | {m_type:<15} | {mem_val:>7.1f}%")
                            count += 1
                    except ValueError:
                        continue
            except Exception as e:
                # print(f"Error processing {m_id}: {e}")
                continue
    
    print("-" * 85)
    print(f"Total resources with memory > 90%: {count}")

if __name__ == '__main__':
    main()
