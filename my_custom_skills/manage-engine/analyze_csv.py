import csv
from collections import defaultdict

def analyze_forecast(csv_file):
    summary = {
        'total_servers': set(),
        'status_counts': defaultdict(int),
        'os_status': defaultdict(lambda: defaultdict(int)),
        'top_cpu': [],
        'top_mem': [],
        'top_disk': [],
        'rapid_growth': []
    }

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                server = row['Server Name']
                os_type = row['OS'].lower()
                metric = row['Metric']
                status = row['Status']
                pred_peak = float(row['Predicted Peak (%)']) if row['Predicted Peak (%)'] else 0.0
                risks = row['Risks']

                summary['total_servers'].add(server)
                summary['status_counts'][status] += 1
                summary['os_status'][os_type][status] += 1

                item = {
                    'server': server,
                    'metric': metric,
                    'pred_peak': pred_peak,
                    'risks': risks
                }

                if 'CPU' in metric:
                    summary['top_cpu'].append(item)
                elif 'Memory' in metric:
                    summary['top_mem'].append(item)
                elif 'Disk' in metric:
                    summary['top_disk'].append(item)

                if 'Rapid Growth' in risks:
                    summary['rapid_growth'].append(item)

    except FileNotFoundError:
        print(f"Error: {csv_file} not found.")
        return

    # Sort top lists
    summary['top_cpu'].sort(key=lambda x: x['pred_peak'], reverse=True)
    summary['top_mem'].sort(key=lambda x: x['pred_peak'], reverse=True)
    summary['top_disk'].sort(key=lambda x: x['pred_peak'], reverse=True)

    # Output
    print(f"Total Servers Analyzed: {len(summary['total_servers'])}")
    print("\n--- Overall Status ---")
    for status, count in summary['status_counts'].items():
        print(f"{status}: {count}")

    print("\n--- Top 5 Critical CPU (Predicted Peak) ---")
    for item in summary['top_cpu'][:5]:
        print(f"{item['server']} - {item['pred_peak']}% ({item['risks']})")

    print("\n--- Top 5 Critical Memory (Predicted Peak) ---")
    for item in summary['top_mem'][:5]:
        print(f"{item['server']} - {item['pred_peak']}% ({item['risks']})")

    print("\n--- Top 5 Critical Disk (Predicted Peak) ---")
    for item in summary['top_disk'][:5]:
        print(f"{item['server']} ({item['metric']}) - {item['pred_peak']}% ({item['risks']})")
    
    if summary['rapid_growth']:
        print("\n--- Rapid Growth Detected ---")
        for item in summary['rapid_growth']:
            print(f"{item['server']} - {item['metric']}: {item['risks']}")

if __name__ == "__main__":
    analyze_forecast('capacity_forecast.csv')
