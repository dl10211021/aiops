import argparse
import logging
import concurrent.futures
import csv
import sys
import os
import statistics
import xml.etree.ElementTree as ET

# Add ManageEngine skill scripts to path to import api
skill_path = os.path.dirname(os.path.abspath(__file__))
if skill_path not in sys.path:
    sys.path.append(skill_path)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('forecast_capacity')

# Attribute Map with Fallbacks
ATTR_MAP = {
    "windows": {
        # 41005: Win2012, 40805: Win2016, 40905: Win2019, 40605: Another Win Variant, 42005: Win11, 40705: Win10, 1977: Win2008, 1307: Win2003, 9641: CPU Core fallback
        "cpu": ["41005", "40805", "40905", "40605", "42005", "40705", "1977", "1307", "9641"],
        # 41003: Win2012, 40803: Win2016, 40903: Win2019, 40603: Another Win Variant, 42003: Win11, 40703: Win10, 1972: Win2008, 1302: Win2003
        "mem": ["41003", "40803", "40903", "40603", "42003", "40703", "1972", "1302"]
    },
    "linux": {
        "cpu": ["708", "9641"],
        "mem": ["702", "685"] # 702 Physical, 685 Total
    },
    "disk": ["711"] # Disk Usage %
}

def get_linear_regression(y_values):
    """Calculate linear regression y = mx + c"""
    n = len(y_values)
    if n < 2:
        return 0, y_values[0] if y_values else 0
        
    x = list(range(n))
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y_values)
    
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y_values))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    
    if denominator == 0:
        return 0, y_mean
        
    m = numerator / denominator
    c = y_mean - (m * x_mean)
    
    return m, c

def parse_history(xml_string):
    """Parses history data into a list of floats."""
    values = []
    if not xml_string or not isinstance(xml_string, str):
        return []
    
    try:
        root = ET.fromstring(xml_string)
        # Handle ArchiveData (Historical)
        for archive in root.findall(".//ArchiveData"):
            val = archive.get("AvgValue")
            if val:
                try:
                    v = float(val)
                    if v >= 0: values.append(v)
                except ValueError:
                    pass
                    
        # Handle Data (Recent)
        if not values:
            for data in root.findall(".//Data"):
                val = data.find("Value")
                if val is not None and val.text:
                    try:
                        v = float(val.text)
                        if v >= 0: values.append(v)
                    except ValueError:
                        pass
    except Exception:
        pass
        
    return values

def analyze_metric(name, values, threshold_warning=80, threshold_critical=90):
    result = {
        "name": name,
        "status": "NODATA",
        "avg": 0,
        "peak": 0,
        "trend": "UNKNOWN",
        "reason": [],
        "curr_avg": 0,
        "curr_max": 0
    }
    
    if not values:
        return result

    # Basic Stats
    curr_avg = statistics.mean(values)
    curr_max = max(values)
    
    # Trend Analysis (Linear Regression)
    slope, intercept = get_linear_regression(values)
    
    n_points = len(values)
    # Assuming data covers 30 days (Period 2), 7 days is approx 7/30 * N steps ahead
    steps_7days = int(n_points * (7/30)) if n_points > 10 else 1
    
    pred_avg = (slope * (n_points + steps_7days)) + intercept
    pred_avg = max(0, pred_avg) # Clamp to 0
    
    # Peak Prediction (Add the max historical deviation to the predicted average)
    peak_buffer = curr_max - curr_avg
    pred_peak = pred_avg + peak_buffer
    
    trend_str = "STABLE"
    if slope > 0.01: trend_str = "RISING"
    elif slope < -0.01: trend_str = "FALLING"
    
    # Assessment
    status = "OK"
    reason = []
    
    if pred_peak > threshold_critical:
        status = "CRITICAL"
        reason.append(f"Peak > {threshold_critical}%")
    elif pred_peak > threshold_warning:
        status = "WARNING"
        reason.append(f"Peak > {threshold_warning}%")
        
    if slope > 0.1 and pred_avg > 50:
        reason.append("Rapid Growth")
        
    result.update({
        "status": status,
        "avg": pred_avg,
        "peak": pred_peak,
        "trend": trend_str,
        "reason": reason,
        "curr_avg": curr_avg,
        "curr_max": curr_max
    })
    
    return result

def fetch_history_task(client, resource_id, attr_ids, period=2):
    """Try a list of attribute IDs until data is found."""
    if isinstance(attr_ids, str): attr_ids = [attr_ids]
    
    for attr_id in attr_ids:
        data = client.get_history_data(resource_id, attr_id, period)
        values = parse_history(data)
        if values:
            return values
    return []

def forecast_server(client, resource_id, os_type):
    """Analyzes a single server resource."""
    results = []
    
    os_key = "windows" if os_type == "windows" else "linux"
    cpu_attrs = ATTR_MAP[os_key]["cpu"]
    mem_attrs = ATTR_MAP[os_key]["mem"]
    
    # Sequential fetch for CPU/Mem to simplify retry logic, but parallelize the server task itself
    # Fetch CPU
    cpu_vals = fetch_history_task(client, resource_id, cpu_attrs)
    results.append(analyze_metric("CPU", cpu_vals))
    
    # Fetch Mem
    mem_vals = fetch_history_task(client, resource_id, mem_attrs)
    results.append(analyze_metric("Memory", mem_vals))
    
    # Fetch Details for Disk (Parallelized if possible, but details call is one)
    try:
        details = client.get_monitor_details(resource_id)
        if details:
            result_obj = details.get('response', {}).get('result', {})
            if isinstance(result_obj, list): result_obj = result_obj[0]
            
            child_monitors = result_obj.get('CHILDMONITORS', [])
            if isinstance(child_monitors, dict): child_monitors = [child_monitors]
            
            disk_ids = []
            
            for group in child_monitors:
                d_name_raw = group.get('DISPLAYNAME', '')
                # Filter for Disk groups
                if any(k in d_name_raw for k in ['磁盘', 'Disk', 'Partition', 'Logical Disk']):
                    children = group.get('CHILDMONITORINFO', [])
                    if isinstance(children, dict): children = [children]
                    
                    for disk in children:
                        # Filter out Swap/Shm/Overlay if needed
                        disk_name = disk.get('DISPLAYNAME', '')
                        disk_id = disk.get('RESOURCEID')
                        
                        # Ignore Linux pseudo filesystems for clarity
                        if os_type == "linux" and any(x in disk_name for x in ['/dev/shm', '/sys/fs/cgroup', 'docker', 'overlay']):
                            continue
                        
                        disk_ids.append((disk_name, disk_id))
            
            # Fetch Disks in Parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as disk_executor:
                 future_to_disk = {
                     disk_executor.submit(fetch_history_task, client, did, ATTR_MAP["disk"]): dname 
                     for dname, did in disk_ids
                 }
                 
                 for future in concurrent.futures.as_completed(future_to_disk):
                     dname = future_to_disk[future]
                     try:
                         vals = future.result()
                         results.append(analyze_metric(f"Disk ({dname})", vals))
                     except Exception:
                         pass

    except Exception as e:
        logger.error(f"Details Fetch Failed for {resource_id}: {e}")
            
    return results

def main():
    parser = argparse.ArgumentParser(description="Forecast Resource Capacity based on 30-day history")
    parser.add_argument("--limit", type=int, default=1000, help="Max number of servers to analyze")
    parser.add_argument("--output", default="forecast.csv", help="Output CSV file")
    
    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info("Fetching list of all monitors...")
    response = client.list_monitors()
    
    windows_servers = []
    linux_servers = []
    skipped_count = 0
    
    if response and 'response' in response and 'result' in response['response']:
        monitors = response['response']['result']
        if isinstance(monitors, dict): monitors = [monitors]
        
        for m in monitors:
            # --- FILTER LOGIC ---
            # 1. Check if Managed
            is_managed = str(m.get('Managed', m.get('MANAGED', 'true'))).lower() == 'true'
            # 2. Check Availability Status (Exclude Down/Maintenance)
            avail_status = str(m.get('AVAILABILITYSTATUS', 'up')).lower()
            
            if not is_managed or avail_status == 'down':
                skipped_count += 1
                continue
            # --------------------
            
            m_type = m.get('TYPE', '').lower()
            name = m.get('DISPLAYNAME', '')
            res_id = m.get('RESOURCEID')
            
            item = {
                'id': res_id,
                'name': name,
                'type': m.get('TYPE'),
            }
            
            if 'windows' in m_type:
                item['os'] = 'windows'
                windows_servers.append(item)
            elif 'linux' in m_type:
                item['os'] = 'linux'
                linux_servers.append(item)

    logger.info(f"Skipped {skipped_count} servers (Down or Unmanaged).")

    # Apply Limits
    selected_servers = windows_servers[:args.limit] + linux_servers[:args.limit]
    logger.info(f"Selected {len(selected_servers)} servers ({len(windows_servers[:args.limit])} Windows, {len(linux_servers[:args.limit])} Linux)")
    
    results_data = []
    
    # Process
    # Use fewer workers to avoid connection pool issues
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_server = {
            executor.submit(forecast_server, client, s['id'], s['os']): s 
            for s in selected_servers
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_server)):
            s = future_to_server[future]
            try:
                server_results = future.result()
                
                for res in server_results:
                    row = {
                        "Server Name": s['name'],
                        "OS": s['os'],
                        "Metric": res['name'],
                        "Status": res['status'],
                        "Current Avg (%)": f"{res.get('curr_avg', 0):.1f}",
                        "Current Max (%)": f"{res.get('curr_max', 0):.1f}",
                        "Predicted Avg (%)": f"{res.get('avg', 0):.1f}",
                        "Predicted Peak (%)": f"{res.get('peak', 0):.1f}",
                        "Trend": res['trend'],
                        "Risks": "; ".join(res['reason'])
                    }
                    results_data.append(row)
                
                if (i+1) % 10 == 0:
                    logger.info(f"[{i+1}/{len(selected_servers)}] Analyzed {s['name']}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {s['name']}: {e}")

    # Write CSV
    if results_data:
        keys = results_data[0].keys()
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results_data)
        
        print(f"\nAnalysis Complete. Report saved to {args.output}")
        print("-" * 60)
        
        # Print Summary
        for os_type in ['windows', 'linux']:
            print(f"\n{os_type.upper()} Summary:")
            risks = [r for r in results_data if r['OS'] == os_type and r['Status'] in ['CRITICAL', 'WARNING']]
            if not risks:
                print("  No major bottlenecks detected.")
            else:
                for r in risks:
                    print(f"  [{r['Status']}] {r['Server Name']} - {r['Metric']}: {r['Risks']} (Pred Peak: {r['Predicted Peak (%)']}%)")

if __name__ == "__main__":
    main()
