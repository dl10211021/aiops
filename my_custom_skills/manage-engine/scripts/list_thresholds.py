import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def list_thresholds():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    response = client.list_threshold_profiles()
    
    print(f"{'ID':<12} | {'Name':<40} | {'Critical':<15} | {'Warning'}")
    print("-" * 90)
    
    if response and 'response' in response and 'result' in response['response']:
        profiles = response['response']['result']
        for p in profiles:
            p_id = p.get('ID', 'N/A')
            p_name = p.get('DISPLAYNAME', 'N/A')
            p_crit = p.get('CRITICALTHRESHOLDVALUE', '-')
            p_warn = p.get('WARNINGTHRESHOLDVALUE', '-')
            p_crit_cond = p.get('CRITICALTHRESHOLDCONDITION', '')
            
            # Format condition nicely
            crit_display = f"{p_crit_cond} {p_crit}" if p_crit != '-' else '-'
            
            print(f"{p_id:<12} | {p_name[:38]:<40} | {crit_display:<15} | {p_warn}")
    else:
        print("Failed to list thresholds.")

if __name__ == "__main__":
    list_thresholds()