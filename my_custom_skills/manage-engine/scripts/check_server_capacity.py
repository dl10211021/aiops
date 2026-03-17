
import argparse
import logging
import statistics
import datetime
import xml.etree.ElementTree as ET
import sys
import os

# Add ManageEngine skill scripts to path
skill_path = os.path.dirname(os.path.abspath(__file__))
if skill_path not in sys.path:
    sys.path.append(skill_path)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('check_server')

# Unified Attribute Map
ATTR_MAP = {
    "windows": {
        "cpu": ["41005", "40805", "40905", "40605", "42005", "40705", "1977", "1307", "9641"],
        "mem": ["41003", "40803", "40903", "40603", "42003", "40703", "1972", "1302"]
    },
    "linux": {
        "cpu": ["708", "9641"],
        "mem": ["702", "685"]
    },
    "disk": ["711"]
}

def get_linear_regression(y_values):
    n = len(y_values)
    if n < 2: return 0, y_values[0] if y_values else 0
    x = list(range(n))
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y_values)
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y_values))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    if denominator == 0: return 0, y_mean
    m = numerator / denominator
    c = y_mean - (m * x_mean)
    return m, c

def parse_history(xml_string):
    values = []
    if not xml_string or not isinstance(xml_string, str): return []
    try:
        root = ET.fromstring(xml_string)
        for archive in root.findall(".//ArchiveData"):
            val = archive.get("AvgValue")
            if val: values.append(float(val))
        for data in root.findall(".//Data"):
            val = data.find("Value")
            if val is not None and val.text: values.append(float(val.text))
    except: pass
    return values

def fetch_history_task(client, resource_id, attr_ids, period=2):
    if isinstance(attr_ids, str): attr_ids = [attr_ids]
    for attr_id in attr_ids:
        data = client.get_history_data(resource_id, attr_id, period)
        values = parse_history(data)
        if values: return values
    return []

def analyze_and_print(name, values):
    if not values:
        print(f"[{name}] No Data")
        return

    curr_avg = statistics.mean(values)
    curr_max = max(values)
    slope, intercept = get_linear_regression(values)
    
    # Forecast 7 days
    n = len(values)
    future_n = n + (n * 7 / 30) # approx
    pred_avg = (slope * future_n) + intercept
    pred_peak = pred_avg + (curr_max - curr_avg)
    
    trend = "Stable"
    if slope > 0.01: trend = "Rising"
    elif slope < -0.01: trend = "Falling"
    
    print(f"[{name}]")
    print(f"  Current Avg: {curr_avg:.1f}% | Max: {curr_max:.1f}%")
    print(f"  Trend: {trend} (Slope: {slope:.4f})")
    print(f"  7-Day Forecast -> Avg: {pred_avg:.1f}% | Peak: {pred_peak:.1f}%")
    
    if pred_peak > 90: print("  🚨 RISK: CRITICAL (Peak > 90%)")
    elif pred_peak > 80: print("  ⚠️ RISK: WARNING (Peak > 80%)")
    print("")

def main():
    parser = argparse.ArgumentParser(description="Check capacity forecast for a single server")
    parser.add_argument("target", help="Server IP or Name (partial match)")
    args = parser.parse_args()
    
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"Searching for {args.target}...")
    response = client.list_monitors()
    
    target = None
    if response and 'response' in response and 'result' in response['response']:
        monitors = response['response']['result']
        if isinstance(monitors, dict): monitors = [monitors]
        
        # Priority 1: Exact IP match or bounded match
        for m in monitors:
            name = m.get('DISPLAYNAME', '')
            if args.target == name or f"_{args.target}_" in name or name.endswith(f"_{args.target}") or args.target in name.split('_'): 
                target = m
                break
        
        # Priority 2: Containment
        if not target:
            import re
            for m in monitors:
                name = m.get('DISPLAYNAME', '')
                if args.target in name:
                    # Avoid 10.10 matching 10.102
                    if not re.search(re.escape(args.target) + r'\d', name):
                        target = m
                        break
    
    if not target:
        print("Server not found.")
        return

    print(f"Found: {target['DISPLAYNAME']} ({target['TYPE']})")
    res_id = target['RESOURCEID']
    os_type = 'windows' if 'windows' in target['TYPE'].lower() else 'linux'
    
    # Analyze
    print("\n--- 7-Day Capacity Forecast ---")
    
    # CPU
    cpu_vals = fetch_history_task(client, res_id, ATTR_MAP[os_type]['cpu'])
    analyze_and_print("CPU", cpu_vals)
    
    # Mem
    mem_vals = fetch_history_task(client, res_id, ATTR_MAP[os_type]['mem'])
    analyze_and_print("Memory", mem_vals)
    
    # Disks
    details = client.get_monitor_details(res_id)
    if details:
        result_obj = details.get('response', {}).get('result', {})
        if isinstance(result_obj, list): result_obj = result_obj[0]
        child_monitors = result_obj.get('CHILDMONITORS', [])
        if isinstance(child_monitors, dict): child_monitors = [child_monitors]
        
        for group in child_monitors:
            if any(k in group.get('DISPLAYNAME', '') for k in ['Disk', '磁盘', 'Partition']):
                children = group.get('CHILDMONITORINFO', [])
                if isinstance(children, dict): children = [children]
                for disk in children:
                    dname = disk.get('DISPLAYNAME')
                    did = disk.get('RESOURCEID')
                    vals = fetch_history_task(client, did, ATTR_MAP["disk"])
                    analyze_and_print(f"Disk ({dname})", vals)

if __name__ == "__main__":
    main()
