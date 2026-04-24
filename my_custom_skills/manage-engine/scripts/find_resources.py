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

def check_resource(client, monitor, args):
    """
    Worker function to check a single resource.
    Returns result dict or None.
    """
    m_id = monitor.get('RESOURCEID')
    m_name = monitor.get('RESOURCENAME', 'Unknown')
    m_disp_name = monitor.get('DISPLAYNAME') or m_name
    m_type = monitor.get('TYPE', 'Unknown')
    
    # Filter by type if needed
    target_os_types = ['Windows', 'Linux', 'Server', 'Solaris', 'AIX', 'HP-UX']
    if args.type == "all" and not any(os_t.lower() in m_type.lower() for os_t in target_os_types):
        return None
    
    if args.type != "all" and args.type.lower() not in m_type.lower():
         return None

    try:
        # Optimized: Use get_monitor_data
        data_response = client.get_monitor_data(m_id)
        if not data_response or 'response' not in data_response or 'result' not in data_response['response']:
            return None
            
        result = data_response['response']['result'][0]
        val = None
        
        # Metric extraction logic
        if args.metric == "cpu":
            val = result.get('CPUUTIL') or result.get('CPUUtilization')
            if not val: 
                    for attr in result.get('Attribute', []):
                        if attr.get('DISPLAYNAME') in ['CPU利用率', 'CPU Utilization', 'CPU Usage']:
                            val = attr.get('Value')
                            break
                            
        elif args.metric == "memory":
            val = result.get('PHYMEMUTIL') or result.get('MEMUTIL')
            if not val:
                for attr in result.get('Attribute', []):
                        if attr.get('DISPLAYNAME') in ['物理内存利用率', 'Physical Memory Utilization', 'Memory Utilization']:
                            val = attr.get('Value')
                            break
                            
        elif args.metric == "disk":
            val = result.get('DISKUTIL') or result.get('Disk Utilization')
            if not val:
                for attr in result.get('Attribute', []):
                        if attr.get('DISPLAYNAME') in ['磁盘利用率', 'Disk Utilization', '总的磁盘利用率(%)', 'Disk Usage']:
                            val = attr.get('Value')
                            break
        
        if val:
            try:
                f_val = float(val)
                if f_val > args.threshold:
                    return {
                        "id": m_id,
                        "name": m_disp_name,
                        "type": m_type,
                        "metric": args.metric,
                        "value": f_val
                    }
            except ValueError:
                pass
    except Exception:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Find ManageEngine resources based on metric thresholds (Multi-threaded).")
    parser.add_argument("--metric", choices=["cpu", "memory", "disk"], required=True, help="Metric to check (cpu, memory, disk)")
    parser.add_argument("--threshold", type=float, default=90.0, help="Threshold percentage (default: 90.0)")
    parser.add_argument("--type", default="all", help="Resource type filter (e.g., servers, Linux, Windows)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--concurrency", type=int, default=20, help="Number of concurrent threads (default: 20)")
    
    args = parser.parse_args()

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    if not args.json:
        print(f"Fetching monitors (Type: {args.type})...")
        
    try:
        response = client.list_monitors(type=args.type)
        if not response or 'response' not in response or 'result' not in response['response']:
            print("Failed to fetch monitors or empty response.")
            return
            
        monitors = response['response']['result']
        # Handle dict vs list
        if isinstance(monitors, dict):
             monitors = [monitors]

        total_monitors = len(monitors)
        
        if not args.json:
            print(f"Scanning {total_monitors} resources with {args.concurrency} threads...")
            print(f"{'ID':<12} | {'Name':<40} | {'Type':<15} | {'Value':<8}")
            print("-" * 85)

        results = []
        count = 0

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_monitor = {executor.submit(check_resource, client, m, args): m for m in monitors}
            
            for future in as_completed(future_to_monitor):
                res = future.result()
                if res:
                    results.append(res)
                    count += 1
                    if not args.json:
                         print(f"{res['id']:<12} | {res['name'][:40]:<40} | {res['type'][:15]:<15} | {res['value']:>7.1f}%")

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("-" * 85)
            print(f"Total resources with {args.metric} > {args.threshold}%: {count}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
