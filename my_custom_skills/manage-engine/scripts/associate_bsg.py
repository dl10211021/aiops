from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def find_bsg_and_associate(target_id="10113062"):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- 正在深度搜索业务组 (BSG) ---")
    
    # 尝试列出所有 Monitor，并专门寻找 BSG 类型
    data = client.list_monitors()
    
    bsg_list = []
    
    if data and 'response' in data and 'result' in data['response']:
        for m in data['response']['result']:
            m_type = m.get('TYPE', '')
            name = m.get('DISPLAYNAME', '')
            res_id = m.get('RESOURCEID', '')
            
            # BSG 通常类型是 'BSG' 或 'BusinessService'
            if 'BSG' in m_type or 'Business' in m_type or 'Service' in m_type:
                bsg_list.append((res_id, name, m_type))
    
    if bsg_list:
        print(f"✅ 发现 {len(bsg_list)} 个业务组:")
        for bid, bname, btype in bsg_list:
            print(f" - [{bid}] {bname} ({btype})")
            
            # 如果名字里包含 'AD' 或 '测试'，我们就尝试关联
            if 'AD' in bname or '测试' in bname:
                print(f"   🎯 目标锁定！尝试将 {target_id} 关联到 {bname}...")
                
                # 尝试通用的关联接口
                # 注意：Business Group 的关联参数通常是 'groupid' 和 'resourceid'
                try:
                    res = client.associate_monitor_to_group(bid, [target_id])
                    print(f"   关联结果: {res}")
                except Exception as e:
                    print(f"   关联失败: {e}")
    else:
        print("❌ 未发现任何业务组 (BSG) 类型资源。")
        print("可能原因：API Key 权限不足，无法查看业务视图。")

if __name__ == "__main__":
    find_bsg_and_associate()
