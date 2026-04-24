from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def list_monitor_groups():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- 正在获取所有监控组 (Monitor Groups) ---")
    
    # 获取所有监控项
    data = client.list_monitors()
    
    if data and 'response' in data and 'result' in data['response']:
        monitors = data['response']['result']
        groups = []
        
        # 筛选出类型为 'Monitor Group' 或类似名称的资源
        for m in monitors:
            m_type = m.get('TYPE', '')
            m_name = m.get('DISPLAYNAME', '')
            m_id = m.get('RESOURCEID', '')
            
            # 常见的组类型标识
            if 'Group' in m_type or 'MonitorGroup' in m_type:
                groups.append({
                    "name": m_name,
                    "id": m_id,
                    "type": m_type,
                    "health": m.get('HEALTHSTATUS', 'unknown')
                })
        
        if groups:
            print(f"✅ 发现 {len(groups)} 个监控组:")
            print("-" * 60)
            print(f"{'ID':<15} | {'组名称':<30} | {'类型':<20} | {'健康状态'}")
            print("-" * 60)
            for g in groups:
                print(f"{g['id']:<15} | {g['name']:<30} | {g['type']:<20} | {g['health']}")
            print("-" * 60)
        else:
            print("⚠️ 未发现任何监控组。")
            print("(提示: 可能是 API 权限限制导致无法列出组，或者系统中尚未创建组)")
            
    else:
        print("❌ API 请求失败或无数据返回。")

if __name__ == "__main__":
    list_monitor_groups()
