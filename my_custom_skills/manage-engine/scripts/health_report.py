import argparse
import sys
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('HealthReport')

def generate_report(show_status=None, verbose=False):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("⏳ 正在获取全局监控数据...")
    data = client.list_monitors()
    
    if not data or 'response' not in data or 'result' not in data['response']:
        logger.error("❌ 获取监控数据失败。")
        return

    # Handle list vs dict in result
    monitors = data['response']['result']
    if isinstance(monitors, dict):
        monitors = [monitors]
        
    total_count = len(monitors)
    status_counts = {}
    type_counts = {}
    
    # Categorize resources
    resources_by_status = {
        'critical': [],
        'warning': [],
        'unknown': [],
        'clear': []
    }

    for m in monitors:
        status = str(m.get('HEALTHSTATUS', 'unknown')).lower()
        m_type = str(m.get('TYPESHORTNAME', m.get('TYPE', 'Unknown')))
        
        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[m_type] = type_counts.get(m_type, 0) + 1
        
        info = {
            'name': m.get('DISPLAYNAME', 'N/A'),
            'type': m_type,
            'ip': m.get('HOSTIP', '-'),
            'id': m.get('RESOURCEID', 'N/A'),
            'message': str(m.get('HEALTHMESSAGE', '-')).replace('<br>', ' ')
        }
        
        if status in resources_by_status:
            resources_by_status[status].append(info)
        else:
            if 'other' not in resources_by_status: resources_by_status['other'] = []
            resources_by_status['other'].append(info)

    # --- Summary Section ---
    print("\n" + "="*70)
    print("      🏥 卓豪 (ManageEngine) 全局健康体检报告")
    print("="*70)
    print(f"📦 监控资源总数: {total_count}")
    
    print("\n[📊 健康状态分布]")
    status_map = {
        "clear": "✅ 正常 (Clear)",
        "critical": "🔴 严重 (Critical)",
        "warning": "⚠️ 警告 (Warning)",
        "unknown": "⚪ 未知 (Unknown)"
    }
    
    for status, label in status_map.items():
        count = status_counts.get(status, 0)
        print(f" - {label:<18}: {count}")

    print("\n[💻 资源类型分布 (前 5 名)]")
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    for m_type, count in sorted_types[:5]:
        print(f" - {m_type:<20}: {count}")

    # --- Detail Section ---
    
    # Determine what to show
    statuses_to_show = []
    if show_status:
        statuses_to_show = [s.lower() for s in show_status.split(',')]
    elif verbose:
        statuses_to_show = ['critical', 'warning', 'unknown']
    else:
        # Default: Show Critical and Warning only (Standard Report)
        statuses_to_show = ['critical', 'warning']

    for status in ['critical', 'warning', 'unknown', 'clear']:
        if status not in statuses_to_show:
            continue
            
        items = resources_by_status.get(status, [])
        if not items: continue
        
        header_label = status_map.get(status, status.upper())
        print(f"\n[🔍 {header_label} 资源详情 - {len(items)} 个]")
        print("-" * 105)
        print(f"{'ID':<12} | {'类型':<18} | {'IP 地址':<16} | {'名称/详情'}")
        print("-" * 105)
        
        for item in items:
            detail = item['name']
            if status != 'clear' and status != 'unknown':
                msg = item['message'][:40]
                detail = f"{item['name']} ({msg}...)"
                
            print(f"{item['id']:<12} | {item['type'][:18]:<18} | {item['ip']:<16} | {detail[:50]}")
        print("-" * 105)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ManageEngine Health Report")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息 (包括未知状态)")
    parser.add_argument("--status", help="过滤特定状态 (如: 'unknown', 'critical,warning')")
    
    args = parser.parse_args()
    
    generate_report(show_status=args.status, verbose=args.verbose)
