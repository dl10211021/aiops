import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def find_group(keyword):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print(f"--- 正在搜索名称包含 '{keyword}' 的资源 ---")
    
    # 获取所有监控项
    # 注意: 业务组 (Business Group) 的类型有时是 'BSG' 或 'MonitorGroup'
    data = client.list_monitors()
    
    found = []
    
    if data and 'response' in data and 'result' in data['response']:
        monitors = data['response']['result']
        for m in monitors:
            name = m.get('DISPLAYNAME', '')
            m_type = m.get('TYPE', '')
            res_id = m.get('RESOURCEID', '')
            
            # 匹配关键字
            if keyword.lower() in name.lower():
                found.append(f"[{res_id}] {name} (类型: {m_type})")
    
    if found:
        print(f"✅ 找到 {len(found)} 个匹配项:")
        for item in found:
            print(" " + item)
    else:
        print("❌ 未找到任何匹配项。")

if __name__ == "__main__":
    # 搜索关键字
    find_group("AD")
    print("-" * 30)
    find_group("测试")
