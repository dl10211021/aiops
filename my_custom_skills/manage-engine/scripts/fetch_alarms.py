import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import json
import re

def clean_html(text):
    if not text: return ""
    return re.sub(r'<[^>]+>', '', str(text)).strip()

def fetch_active_alarms():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- Fetching Active Alarms ---")
    
    # 获取 Critical 告警
    critical_data = client.list_alarms(type="critical")
    # 获取 Warning 告警
    warning_data = client.list_alarms(type="warning")
    
    all_alarms = []
    
    # Process Critical
    if critical_data and 'response' in critical_data and 'result' in critical_data['response']:
        result = critical_data['response']['result']
        # Handle single object vs list
        if isinstance(result, dict): result = [result]
        for alarm in result:
            alarm['severity'] = 'CRITICAL'
            all_alarms.append(alarm)
            
    # Process Warning
    if warning_data and 'response' in warning_data and 'result' in warning_data['response']:
        result = warning_data['response']['result']
        if isinstance(result, dict): result = [result]
        for alarm in result:
            alarm['severity'] = 'WARNING'
            all_alarms.append(alarm)
            
    if not all_alarms:
        print("✅ No active alarms found.")
        return

    # Sort by time desc
    try:
        all_alarms.sort(key=lambda x: int(x.get('MODTIME', 0)), reverse=True)
    except:
        pass 
        
    print(f"\nFound {len(all_alarms)} active alarms:\n")
    
    # Header
    print(f"{'SEV':<4} | {'TIME':<20} | {'RESOURCE':<30} | {'MESSAGE'}")
    print("-" * 100)
    
    for alarm in all_alarms:
        severity = alarm.get('severity', 'UNK')
        sev_icon = "🔴" if severity == 'CRITICAL' else "🟠"
        
        time_str = alarm.get('FORMATTEDDATE', 'Unknown')
        name = alarm.get('DISPLAYNAME', 'Unknown')
        msg = clean_html(alarm.get('MESSAGE', ''))
        
        # Truncate
        name_short = (name[:28] + '..') if len(name) > 28 else name
        msg_short = (msg[:60] + '..') if len(msg) > 60 else msg
        
        print(f"{sev_icon} {severity:<4} | {time_str:<20} | {name_short:<30} | {msg_short}")

if __name__ == "__main__":
    fetch_active_alarms()
