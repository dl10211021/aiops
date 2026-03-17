import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import re

def get_alarm_details(resource_name):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    # Try both warning and critical to be sure
    for severity in ["warning", "critical"]:
        alarms = client.list_alarms(type=severity)
        
        if alarms and 'response' in alarms and 'result' in alarms['response']:
            # Handle potential single result dict vs list
            result_list = alarms['response']['result']
            if isinstance(result_list, dict): result_list = [result_list]
            
            for alarm in result_list:
                if resource_name in alarm.get('DISPLAYNAME', ''):
                    print(f"--- Full Alarm Message ({severity.upper()}) ---")
                    msg = alarm.get('MESSAGE', '')
                    # Replace HTML line breaks with newlines
                    clean_msg = msg.replace('<br>', '\n').replace('<br/>', '\n')
                    # Remove other HTML tags
                    clean_msg = re.sub(r'<[^>]+>', '', clean_msg).strip()
                    print(clean_msg)
                    return

    print("No active alarms found for this resource.")

if __name__ == "__main__":
    get_alarm_details("CNSMFFLUXDB1P_192.168.129.13")
