import json
import sys
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def get_oracle_storage_report(resource_id):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(resource_id)
    
    if not data or 'response' not in data or 'result' not in data['response']:
        print("Failed to retrieve data.")
        return

    result = data['response']['result'][0]
    
    print(f"--- Storage Report for: {result.get('DISPLAYNAME')} ---")
    print(f"Last Poll: {result.get('LASTPOLLEDTIME')}\n")

    # --- 1. Disk Groups (ASM) ---
    print("--- ASM Disk Groups ---")
    print(f"{'Name':<15} | {'Status':<10} | {'Total (GB)':<12} | {'Used (GB)':<12} | {'Used %':<10}")
    print("-" * 70)
    
    disk_groups = []
    if 'CHILDMONITORS' in result:
        for cm in result['CHILDMONITORS']:
            if cm.get('DISPLAYNAME') == 'OracleDiskGroups' and 'CHILDMONITORINFO' in cm:
                disk_groups = cm['CHILDMONITORINFO']
                break
    
    for dg in disk_groups:
        name = dg.get('DISPLAYNAME', 'Unknown')
        attrs = {attr['DISPLAYNAME']: attr['Value'] for attr in dg.get('CHILDATTRIBUTES', [])}
        
        status = attrs.get('状态', 'Unknown')
        if status == 'Unknown': status = attrs.get('Status', 'Unknown')
        # Fallback to AttributeID 2964 for Status if name lookup fails
        if status == 'Unknown':
             for attr in dg.get('CHILDATTRIBUTES', []):
                 if str(attr.get('AttributeID')) == '2964':
                     status = attr.get('Value')

        total = "N/A"
        used = "N/A"
        pct = "N/A"

        for attr in dg.get('CHILDATTRIBUTES', []):
            aid = str(attr.get('AttributeID'))
            val = str(attr.get('Value'))
            if aid == '2966': total = val # Total Disk
            if aid == '75582': used = val # Used Disk
            if aid == '2968': pct = val   # Used %

        # Highlight high usage
        mark = ""
        try:
            if float(pct) >= 90: mark = "🔴"
            elif float(pct) >= 80: mark = "⚠️"
        except: pass
        
        print(f"{mark:<2} {name:<13} | {status:<10} | {total:<12} | {used:<12} | {pct:<10}")

    print("\n")

    # --- 2. Tablespaces ---
    print("--- Tablespaces ---")
    print(f"{'Name':<25} | {'Status':<10} | {'Allocated (MB)':<15} | {'Used (MB)':<12} | {'Used %':<10}")
    print("-" * 80)
    
    tablespaces = []
    if 'CHILDMONITORS' in result:
        for cm in result['CHILDMONITORS']:
            if cm.get('DISPLAYNAME') == 'TableSpace' and 'CHILDMONITORINFO' in cm:
                tablespaces = cm['CHILDMONITORINFO']
                break
                
    for ts in tablespaces:
        name = ts.get('DISPLAYNAME', 'Unknown')
        
        status = "Unknown"
        used_pct = "N/A"
        used_mb = "N/A"
        alloc_mb = "N/A"
        
        for attr in ts.get('CHILDATTRIBUTES', []):
            aid = str(attr.get('AttributeID'))
            val = str(attr.get('Value'))
            
            if aid == '2447': status = val      # Status
            if aid == '2446': used_pct = val    # Used %
            if aid == '2445': used_mb = val     # Used MB
            if aid == '3000': alloc_mb = val    # Allocated MB

        # Highlight high usage
        mark = ""
        try:
            if float(used_pct) >= 90: mark = "🔴"
            elif float(used_pct) >= 80: mark = "⚠️"
        except: pass
        
        print(f"{mark:<2} {name:<23} | {status:<10} | {alloc_mb:<15} | {used_mb:<12} | {used_pct:<10}")

if __name__ == "__main__":
    get_oracle_storage_report("10058525")
