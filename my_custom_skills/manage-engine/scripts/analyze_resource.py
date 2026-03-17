import sys
import argparse
import re
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def clean_html(text):
    if not text: return ""
    return re.sub('<[^<]+?>', '', str(text)).strip()

def analyze_resource(query, days=7):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    # --- 1. 解析资源 ---
    print(f"--- [SEARCH] 正在分析资源: {query} ---")
    resource_id = query
    display_name = query
    resource_type = "未知"
    
    if not query.isdigit():
        monitors = client.list_monitors()
        found = False
        if monitors and 'response' in monitors and 'result' in monitors['response']:
            for m in monitors['response']['result']:
                if query in m.get('HOSTIP', '') or query in m.get('DISPLAYNAME', ''):
                    resource_id = m.get('RESOURCEID')
                    display_name = m.get('DISPLAYNAME')
                    resource_type = m.get('TYPE')
                    found = True
                    break
        if not found:
             print(f"❌ 未找到匹配的监控资源: '{query}'")
             return
    else:
        # ID lookup
        data = client.get_monitor_data(resource_id)
        if data and 'response' in data and 'result' in data['response']:
             if len(data['response']['result']) > 0:
                 res = data['response']['result'][0]
                 display_name = res.get('DISPLAYNAME')
                 resource_type = res.get('TYPE')

    print(f"目标: {display_name} (ID: {resource_id}) | 类型: {resource_type}")

    # --- 2. 当前状态与性能 ---
    print(f"\n--- 📊 当前状态 ---")
    data = client.get_monitor_data(resource_id)
    if data and 'response' in data and 'result' in data['response'] and len(data['response']['result']) > 0:
        info = data['response']['result'][0]
        
        health = info.get('HEALTHSTATUS', 'unknown').lower()
        avail = info.get('AVAILABILITYSTATUS', 'unknown').lower()
        last_poll = info.get('LASTPOLLEDTIME', '未知')
        
        # Status Translation
        status_cn = {
            "clear": "✅ 正常", "critical": "🔴 严重", "warning": "⚠️ 警告", "unknown": "⚪ 未知",
            "up": "✅ 运行中", "down": "🔴 宕机"
        }
        
        print(f"健康状况:     {status_cn.get(health, health)}")
        print(f"可用性:       {status_cn.get(avail, avail)}")
        print(f"最后更新:     {last_poll}")
        
        # Snapshot Metrics
        cpu = info.get('CPUUTIL')
        mem = info.get('PHYMEMUTIL')
        disk = info.get('DISKUTIL')
        
        if cpu or mem or disk:
            print(f"\n[性能快照]")
            if cpu: print(f"  CPU 使用率:    {cpu}%")
            if mem: print(f"  内存 使用率:   {mem}%")
            if disk: print(f"  磁盘 使用率:   {disk}%")
        
        # Key Attributes (First 15)
        if 'Attribute' in info:
            print(f"\n[关键指标]")
            count = 0
            for attr in info['Attribute']:
                if count >= 15: break
                name = attr.get('DISPLAYNAME')
                val = attr.get('Value')
                units = attr.get('Units', '')
                if name and val:
                    print(f"  {name:<25}: {val}{units}")
                    count += 1
    else:
        print("⚠️ 无法获取性能数据。")

    # --- 3. 告警历史 ---
    print(f"\n--- 🔔 告警历史 (最近 {days} 天活跃) ---")
    alarms = client.list_alarms(type="all")
    
    active_alarms = []
    
    if alarms and 'response' in alarms and 'result' in alarms['response']:
        results = alarms['response']['result']
        for alarm in results:
            a_res_id = alarm.get('RESOURCEID')
            a_display = alarm.get('DISPLAYNAME', '')
            
            # Match Logic
            if str(a_res_id) == str(resource_id) or (display_name and display_name in a_display):
                active_alarms.append(alarm)
    
    if active_alarms:
        print(f"发现 {len(active_alarms)} 条相关记录:")
        for alarm in active_alarms[:10]: # Limit to 10
            severity = alarm.get('STATUS', 'unknown').lower()
            time_str = alarm.get('FORMATTEDDATE', '')
            msg = clean_html(alarm.get('MESSAGE', ''))
            
            prefix = "[信息]"
            if severity == 'critical': prefix = "[严重]"
            elif severity == 'warning': prefix = "[警告]"
            elif severity == 'clear': prefix = "[恢复]"
            
            print(f"{prefix:<8} {time_str:<20} | {msg[:80]}...")
    else:
        print("✅ 无活跃告警记录。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_resource.py <IP或ID>")
    else:
        analyze_resource(sys.argv[1])