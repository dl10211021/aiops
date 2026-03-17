
import argparse
import logging
import concurrent.futures
import csv
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
from forecast_resource import forecast_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('batch_forecast')

def main():
    parser = argparse.ArgumentParser(description="Batch Forecast Resource Usage for All Servers")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent servers to analyze (Default: 3)")
    parser.add_argument("--output", default="forecast_report.csv", help="Output CSV file (Default: forecast_report.csv)")
    parser.add_argument("--filter", help="Filter by server name (optional)")
    
    args = parser.parse_args()
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    logger.info("Fetching list of all monitors...")
    response = client.list_monitors()
    
    servers = []
    if response and 'response' in response and 'result' in response['response']:
        monitors = response['response']['result']
        if isinstance(monitors, dict): monitors = [monitors]
        
        for m in monitors:
            m_type = m.get('TYPE', '').lower()
            name = m.get('DISPLAYNAME', '')
            
            # Filter logic
            if args.filter and args.filter.lower() not in name.lower():
                continue
            
            # Identify OS
            os_type = None
            if 'windows' in m_type:
                os_type = 'windows'
            elif 'linux' in m_type:
                os_type = 'linux'
            
            if os_type:
                servers.append({
                    'id': m.get('RESOURCEID'),
                    'name': name,
                    'type': m.get('TYPE'),
                    'os': os_type
                })
    
    logger.info(f"Found {len(servers)} servers to analyze.")
    
    results_data = []
    
    # Analyze in parallel
    # Note: forecast_server uses its own internal thread pool of 5 threads.
    # So 3 workers here means potentially 15 concurrent API calls.
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_server = {
            executor.submit(forecast_server, client, s['id'], s['os']): s 
            for s in servers
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_server)):
            s = future_to_server[future]
            try:
                server_results = future.result()
                
                # Flatten results for CSV
                # Each metric (CPU, Mem, Disk C, Disk D) becomes a row
                for res in server_results:
                    row = {
                        "Server Name": s['name'],
                        "OS": s['type'],
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
                
                logger.info(f"[{i+1}/{len(servers)}] Completed analysis for {s['name']}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {s['name']}: {e}")

    # Write CSV
    if results_data:
        keys = results_data[0].keys()
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results_data)
        logger.info(f"Report generated: {args.output}")
        
        # Print Summary to Console
        critical_count = sum(1 for r in results_data if r['Status'] == 'CRITICAL')
        warning_count = sum(1 for r in results_data if r['Status'] == 'WARNING')
        print(f"\n--- Batch Analysis Complete ---")
        print(f"Total Metrics Analyzed: {len(results_data)}")
        print(f"Critical Risks: {critical_count}")
        print(f"Warnings: {warning_count}")
        print(f"Full report saved to {args.output}")
        
        if critical_count > 0:
            print("\n[CRITICAL RISKS DETECTED]")
            for r in results_data:
                if r['Status'] == 'CRITICAL':
                    print(f" - {r['Server Name']} [{r['Metric']}]: {r['Risks']}")

if __name__ == "__main__":
    main()
