import argparse
import sys
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def check_missing_attributes(client, monitor):
    m_id = monitor.get('RESOURCEID')
    m_name = monitor.get('DISPLAYNAME') or monitor.get('RESOURCENAME', 'Unknown')
    m_type = monitor.get('TYPE', 'Unknown')
    
    # Filter only servers
    if m_type not in ['Windows', 'Linux', 'Server', 'Solaris', 'AIX', 'HP-UX']:
        return None

    try:
        data_response = client.get_monitor_data(m_id)
        if not data_response or 'response' not in data_response or 'result' not in data_response['response']:
            return None
            
        result = data_response['response']['result'][0]
        
        has_cpu = False
        has_mem = False
        has_disk = False
        
        # Check top level first
        if result.get('CPUUTIL') or result.get('CPUUtilization'): has_cpu = True
        if result.get('PHYMEMUTIL') or result.get('MEMUTIL'): has_mem = True
        if result.get('DISKUTIL') or result.get('Disk Utilization'): has_disk = True
        
        # Check Attributes
        if not (has_cpu and has_mem and has_disk):
            for attr in result.get('Attribute', []):
                aid = str(attr.get('AttributeID', ''))
                name = attr.get('DISPLAYNAME', '')
                
                if aid == '708' or 'CPU' in name: has_cpu = True
                if aid == '685' or 'Memory' in name or '内存' in name: has_mem = True
                if aid == '711' or 'Disk' in name or '磁盘' in name: has_disk = True

        missing = []
        if not has_cpu: missing.append("CPU")
        if not has_mem: missing.append("Memory")
        if not has_disk: missing.append("Disk")
        
        if missing:
            return {
                "id": m_id,
                "name": m_name,
                "type": m_type,
                "missing": ", ".join(missing)
            }
            
    except Exception:
        pass
    return None

def main():
    print("Fetching monitors...")
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    response = client.list_monitors()
    monitors = response['response']['result']
    
    print(f"Scanning {len(monitors)} servers for missing metrics...")
    print(f"{'ID':<12} | {'Name':<35} | {'Type':<15} | {'Missing Metrics'}")
    print("-" * 100)
    
    count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_monitor = {executor.submit(check_missing_attributes, client, m): m for m in monitors}
        
        for future in as_completed(future_to_monitor):
            res = future.result()
            if res:
                print(f"{res['id']:<12} | {res['name'][:35]:<35} | {res['type'][:15]:<15} | {res['missing']}")
                count += 1
                
    print("-" * 100)
    print(f"Found {count} servers with missing metrics.")

if __name__ == "__main__":
    main()
