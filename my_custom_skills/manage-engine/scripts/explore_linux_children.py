from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def explore_children(resource_id="10113062"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"--- 深入挖掘服务器 {resource_id} 的子组件指标 ---")
    
    # 获取子监控项
    data = client.get_child_monitors(resource_id)
    
    if data and 'response' in data and 'result' in data['response']:
        children = data['response']['result']
        print(f"找到 {len(children)} 个子监控项：")
        print("-" * 60)
        
        for child in children:
            name = child.get('DISPLAYNAME')
            c_type = child.get('TYPESHORTNAME')
            status = child.get('HEALTHSTATUS')
            msg = child.get('HEALTHMESSAGE', '')
            
            print(f"组件: {name:<30} | 类型: {c_type:<15} | 状态: {status}")
            if 'warning' in str(status).lower() or 'critical' in str(status).lower():
                print(f"   ↳ 告警详情: {msg}")
                
        print("-" * 60)
    else:
        print(" ! 未发现子组件，或该版本 API 不支持从此路径获取子项。")

if __name__ == "__main__":
    explore_children()
