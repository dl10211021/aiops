import argparse
import requests
import json
import sys
import time
from datetime import datetime, timedelta

def get_timestamp(time_str):
    """Parses time string to timestamp. Supports relative (e.g., 1h, 30m) or ISO format."""
    if not time_str:
        return None
    
    if time_str.endswith('m'):
        return time.time() - (int(time_str[:-1]) * 60)
    elif time_str.endswith('h'):
        return time.time() - (int(time_str[:-1]) * 3600)
    elif time_str.endswith('d'):
        return time.time() - (int(time_str[:-1]) * 86400)
    elif time_str == 'now':
        return time.time()
        
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except ValueError:
        pass
        
    try:
        return float(time_str)
    except ValueError:
        print(f"Error: Could not parse time '{time_str}'", file=sys.stderr)
        sys.exit(1)

def query_prometheus(base_url, query, query_type='instant', start=None, end=None, step='1m'):
    base_url = base_url.rstrip('/')
    params = {'query': query}
    
    if query_type == 'range':
        endpoint = '/api/v1/query_range'
        if not end: end = time.time()
        else: end = get_timestamp(end)
        if not start: start = end - 3600
        else: start = get_timestamp(start)
        params['start'] = start
        params['end'] = end
        params['step'] = step
    else:
        endpoint = '/api/v1/query'
        if start: params['time'] = get_timestamp(start)

    try:
        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "errorType": "connection_error", "error": str(e)}

def analyze_system(base_url):
    """Runs a suite of health checks against Prometheus."""
    checks = {
        "up_status": "count(up == 1) / count(up) * 100",
        "cpu_usage_top5": "topk(5, 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100))",
        "memory_usage_top5": "topk(5, (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100)",
        "disk_fullness_top5": "topk(5, 100 - (node_filesystem_free_bytes / node_filesystem_size_bytes * 100))",
        "high_load_top5": "topk(5, node_load1)",
        "network_traffic_in": "topk(5, irate(node_network_receive_bytes_total[5m]))",
    }
    
    report = {}
    for name, query in checks.items():
        res = query_prometheus(base_url, query)
        if res.get('status') == 'success':
            data = res.get('data', {}).get('result', [])
            # Simplify output
            simple_data = []
            for item in data:
                metric = item.get('metric', {})
                # Try to find a meaningful label
                label = metric.get('instance') or metric.get('job') or metric.get('device') or 'unknown'
                value = item.get('value', [0, 0])[1]
                simple_data.append({"label": label, "value": value})
            report[name] = simple_data
        else:
            report[name] = "Query Failed"
            
    return report

def main():
    parser = argparse.ArgumentParser(description='Query Prometheus API')
    parser.add_argument('--url', required=True, help='Prometheus base URL')
    
    subparsers = parser.add_subparsers(dest='command')
    
    # Query Command
    p_query = subparsers.add_parser('query', help='Run PromQL')
    p_query.add_argument('query_string', help='PromQL query')
    p_query.add_argument('--type', choices=['instant', 'range'], default='instant')
    p_query.add_argument('--start')
    p_query.add_argument('--end')
    p_query.add_argument('--step', default='1m')
    p_query.add_argument('--limit', type=int)

    # Analyze Command
    p_analyze = subparsers.add_parser('analyze', help='Run System Health Analysis')

    args = parser.parse_args()

    if args.command == 'analyze':
        report = analyze_system(args.url)
        print(json.dumps(report, indent=2))
    elif args.command == 'query' or not args.command: # Default to query if pos arg provided (for backward compat logic)
        # Handle the case where user might use old syntax without 'query' subcommand
        # Actually argparse handles this strictly if subparsers are used.
        # Let's adjust to be compatible or strict.
        # To be safe, let's keep the old argument structure as top level if command is missing? 
        # No, let's switch to subcommand pattern for clarity as per linux-admin.
        # But wait, the previous version didn't use subcommands.
        # Let's support both: if 'query' is not first arg, assume legacy mode (but argparse makes this hard).
        # Let's stick to the previous simple structure but add --analyze flag.
        pass

    # RE-IMPLEMENTING main with --analyze flag instead of subparsers to maintain backward compatibility
    # if the user relies on `query_prometheus.py --url ... --query ...`
    
    # Reset parser
    parser = argparse.ArgumentParser(description='Query Prometheus API')
    parser.add_argument('--url', required=True, help='Prometheus base URL')
    
    # Mutually exclusive: Query string OR --analyze flag
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--query', help='PromQL query')
    group.add_argument('--analyze', action='store_true', help='Run comprehensive system analysis')
    
    parser.add_argument('--type', choices=['instant', 'range'], default='instant')
    parser.add_argument('--start')
    parser.add_argument('--end')
    parser.add_argument('--step', default='1m')
    parser.add_argument('--limit', type=int)

    args = parser.parse_args()

    if args.analyze:
        report = analyze_system(args.url)
        print(json.dumps(report, indent=2))
    else:
        result = query_prometheus(
            args.url, 
            args.query, 
            query_type=args.type, 
            start=args.start, 
            end=args.end, 
            step=args.step
        )
        if args.limit and result.get('status') == 'success' and 'data' in result and 'result' in result['data']:
            result['data']['result'] = result['data']['result'][:args.limit]
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
