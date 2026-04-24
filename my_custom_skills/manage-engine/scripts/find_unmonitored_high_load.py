import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def check_resource(client, monitor):
    """
    Worker function to check a single resource for high load without alerts.
    """
    m_id = monitor.get('RESOURCEID')
    m_name = monitor.get('RESOURCENAME', 'Unknown')
    m_disp_name = monitor.get('DISPLAYNAME') or m_name
    m_type = monitor.get('TYPE', 'Unknown')
    m_status = monitor.get('HEALTHSTATUS', 'unknown').lower()

    # We are interested in resources that are CLEAR but have high load
    # OR resources that are UNKNOWN (might not be monitored correctly)
    
    # Filter by type (only servers)
    target_os_types = ['Windows', 'Linux', 'Server', 'Solaris', 'AIX', 'HP-UX']
    if not any(os_t.lower() in m_type.lower() for os_t in target_os_types):
        return None

    try:
        data_response = client.get_monitor_data(m_id)
        if not data_response or 'response' not in data_response or 'result' not in data_response['result']:
            return None
        
        result = data_response['result'][0]
        
        # Get metrics
        cpu = result.get('CPUUTIL') or result.get('CPUUtilization')
        mem = result.get('PHYMEMUTIL') or result.get('MEMUTIL')
        disk = result.get('DISKUTIL') or result.get('Disk Utilization')
        
        # Helper to extract from Attributes if not in main dict
        if not cpu:
             for attr in result.get('Attribute', []):
                 if attr.get('AttributeID') == '708': # Standard CPU
                     cpu = attr.get('Value')
                     break
        if not mem:
             for attr in result.get('Attribute', []):
                 if attr.get('AttributeID') == '685': # Standard Mem
                     mem = attr.get('Value')
                     break
        if not disk:
             for attr in result.get('Attribute', []):
                 if attr.get('AttributeID') == '711': # Standard Disk
                     disk = attr.get('Value')
                     break

        # Define high load threshold (e.g., > 80%)
        # If load > 80% AND status is 'clear', it's likely unmonitored or threshold is too high
        threshold = 80.0
        
        issues = []
        
        if cpu:
            try:
                if float(cpu) > threshold and m_status == 'clear':
                    issues.append(f"CPU: {cpu}% (Status: Clear)")
            except: pass
            
        if mem:
            try:
                if float(mem) > threshold and m_status == 'clear':
                    issues.append(f"Mem: {mem}% (Status: Clear)")
            except: pass
            
        if disk:
            try:
                if float(disk) > threshold and m_status == 'clear':
                    issues.append(f"Disk: {disk}% (Status: Clear)")
            except: pass

        if issues:
            return {
                "id": m_id,
                "name": m_disp_name,
                "type": m_type,
                "ip": monitor.get('HOSTIP', '-'),
                "issues": ", ".join(issues)
            }
            
    except Exception:
        pass
    return None

def main():
    print("Fetching monitors...")
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    response = client.list_monitors()
    if not response or 'response' not in response or 'result' not in response['response']:
        print("Failed to fetch monitors.")
        return
        
    monitors = response['response']['result']
    print(f"Scanning {len(monitors)} resources for unmonitored high load (CPU/Mem/Disk > 80% but Status is Clear)...")
    
    print(f"{'ID':<12} | {'Name':<35} | {'Type':<15} | {'Issues'}")
    print("-" * 100)
    
    count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_monitor = {executor.submit(check_resource, client, m): m for m in monitors}
        
        for future in as_completed(future_to_monitor):
            res = future.result()
            if res:
                print(f"{res['id']:<12} | {res['name'][:35]:<35} | {res['type'][:15]:<15} | {res['issues']}")
                count += 1
                
    print("-" * 100)
    print(f"Found {count} potential unmonitored high-load resources.")

if __name__ == "__main__":
    main()
