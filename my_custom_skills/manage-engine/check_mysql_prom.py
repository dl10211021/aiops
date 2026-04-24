import requests

def check_prometheus():
    url = "http://192.168.130.45:9090/api/v1/targets"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            active_targets = data.get('data', {}).get('activeTargets', [])
            mysql_targets = [t for t in active_targets if 'mysql' in t['labels'].get('job', '').lower() or 'mysql' in t['labels'].get('instance', '').lower()]
            
            print(f"Found {len(mysql_targets)} MySQL targets in Prometheus.")
            for t in mysql_targets:
                print(f"- Job: {t['labels'].get('job')}, Instance: {t['labels'].get('instance')}, Health: {t['health']}")
                
            # If found, try to query some metrics
            if mysql_targets:
                print("\nQuerying basic metrics:")
                queries = {
                    "Uptime": "mysql_global_status_uptime",
                    "Threads Connected": "mysql_global_status_threads_connected",
                    "Slow Queries": "mysql_global_status_slow_queries",
                    "QPS": "rate(mysql_global_status_questions[5m])"
                }
                
                for name, query in queries.items():
                    q_url = f"http://192.168.130.45:9090/api/v1/query?query={query}"
                    try:
                        q_res = requests.get(q_url, timeout=5)
                        if q_res.status_code == 200:
                            q_data = q_res.json()
                            results = q_data.get('data', {}).get('result', [])
                            if results:
                                for r in results:
                                    # Filter by instance if possible, or just print all
                                    instance = r['metric'].get('instance', 'unknown')
                                    value = r['value'][1]
                                    print(f"  {name} ({instance}): {value}")
                            else:
                                print(f"  {name}: No data")
                    except Exception as e:
                        print(f"  {name}: Error querying - {e}")

        else:
            print(f"Failed to fetch targets: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to Prometheus: {e}")

if __name__ == "__main__":
    check_prometheus()
