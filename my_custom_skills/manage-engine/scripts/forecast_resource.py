import argparse
import logging
import statistics
import xml.etree.ElementTree as ET
import concurrent.futures
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('forecast')

# Attribute Map based on previous discovery
ATTR_MAP = {
    "win_cpu": "41005",      # Windows CPU Utilization
    "linux_cpu": "708",      # Linux CPU Utilization
    "mem": "41003",          # Physical Memory Utilization
    "disk_percent": "711"    # Disk Utilization % (Usually for child disk monitors)
}

def get_linear_regression(y_values):
    """
    Calculate linear regression y = mx + c
    Returns (slope m, intercept c)
    Assumes x is 0, 1, 2, ... len(y)-1
    """
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
                    values.append(float(val))
                except ValueError:
                    pass
                    
        # Handle Data (Recent)
        if not values:
            for data in root.findall(".//Data"):
                val = data.find("Value")
                if val is not None and val.text:
                    try:
                        values.append(float(val.text))
                    except ValueError:
                        pass
    except Exception as e:
        logger.error(f"XML Parse Error: {e}")
        
    return values

def analyze_metric(name, values, threshold_warning=80, threshold_critical=90):
    result = {
        "name": name,
        "status": "NODATA",
        "avg": 0,
        "peak": 0,
        "trend": "UNKNOWN",
        "reason": []
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
    
    # Peak Prediction
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

def print_analysis(res):
    if res['status'] == 'NODATA':
        print(f"[{res['name']}] No data available.")
        return

    print(f"--- {res['name']} Analysis ---")
    print(f"History (30 Days): Avg: {res['curr_avg']:.1f}% | Max: {res['curr_max']:.1f}% | Trend: {res['trend']}")
    print("Prediction (7 Days):")
    print(f"  > Expected Avg: {res['avg']:.1f}%")
    print(f"  > Potential Peak: {res['peak']:.1f}%")
    
    if res['status'] == "OK":
        print("[OK] STATUS: HEALTHY.")
    else:
        print(f"[ALERT] STATUS: {res['status']}. Risks: {', '.join(res['reason'])}")
    print("")

def fetch_history_task(client, resource_id, attr_id, period):
    """Helper for parallel execution."""
    return client.get_history_data(resource_id, attr_id, period)

def forecast_server(client, resource_id, os_type):
    """
    Analyzes a single server resource.
    Returns a list of analysis results (dicts).
    """
    results = []
    
    cpu_attr = ATTR_MAP["win_cpu"] if os_type == "windows" else ATTR_MAP["linux_cpu"]
    mem_attr = ATTR_MAP["mem"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit CPU and Mem tasks
        future_cpu = executor.submit(fetch_history_task, client, resource_id, cpu_attr, 2)
        future_mem = executor.submit(fetch_history_task, client, resource_id, mem_attr, 2)
        
        # Submit Details task (to find disks)
        future_details = executor.submit(client.get_monitor_details, resource_id)
        
        # Process CPU
        try:
            cpu_res = analyze_metric("CPU", parse_history(future_cpu.result()))
            results.append(cpu_res)
        except Exception as e:
            logger.error(f"CPU Fetch Failed: {e}")
        
        # Process Mem
        try:
            mem_res = analyze_metric("Memory", parse_history(future_mem.result()))
            results.append(mem_res)
        except Exception as e:
            logger.error(f"Mem Fetch Failed: {e}")
        
        # Process Details -> Disks
        try:
            details = future_details.result()
            if details:
                result = details.get('response', {}).get('result', {})
                if isinstance(result, list): result = result[0]
                child_monitors = result.get('CHILDMONITORS', [])
                
                disk_tasks = {}
                
                for group in child_monitors:
                    # Heuristic for finding Disk monitors
                    d_name_raw = group.get('DISPLAYNAME', '')
                    if '磁盘' in d_name_raw or 'Disk' in d_name_raw or 'Partition' in d_name_raw:
                        for disk in group.get('CHILDMONITORINFO', []):
                            disk_name = disk.get('DISPLAYNAME')
                            disk_id = disk.get('RESOURCEID')
                            
                            # Submit Disk Task
                            dt = executor.submit(fetch_history_task, client, disk_id, ATTR_MAP["disk_percent"], 2)
                            disk_tasks[dt] = disk_name
                            
                if disk_tasks:
                    for future in concurrent.futures.as_completed(disk_tasks):
                        d_name = disk_tasks[future]
                        try:
                            d_res = analyze_metric(f"Disk ({d_name})", parse_history(future.result()))
                            results.append(d_res)
                        except Exception as e:
                            logger.error(f"Error processing disk {d_name}: {e}")
        except Exception as e:
            logger.error(f"Details Fetch Failed: {e}")
            
    return results

def main():
    parser = argparse.ArgumentParser(description="Forecast Resource Usage")
    parser.add_argument("resource_id", help="Parent Resource ID")
    parser.add_argument("--os", choices=["windows", "linux"], default="windows", help="OS Type")
    
    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"Generating 7-Day Forecast for Resource {args.resource_id}..\n")
    
    analysis_results = forecast_server(client, args.resource_id, args.os)
    
    for res in analysis_results:
        print_analysis(res)

if __name__ == "__main__":
    main()