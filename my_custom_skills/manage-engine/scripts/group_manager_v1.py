import requests
import xml.etree.ElementTree as ET
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

def manage_group_v1(target_id, group_name="test"):
    # 1. 构建专门针对 v1 XML 接口的 URL
    # 注意：v1 接口通常使用 /AppManager/xml/ 路径
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml"
    
    print(f"--- 尝试使用 v1 XML 接口管理组: '{group_name}' ---")
    
    # --- 步骤 A: 尝试创建组 ---
    # API: AddMonitorGroup
    # Ref: help/add-monitor-group.html
    create_url = f"{base_url}/AddMonitorGroup"
    params = {
        "apikey": DEFAULT_API_KEY,
        "grouptype": "monitorgroup",
        "name": group_name,
        "description": "Created by Gemini CLI"
    }
    
    print(f"1. 创建组请求: {create_url}")
    try:
        res = requests.post(create_url, params=params, verify=False)
        print(f"   HTTP 状态码: {res.status_code}")
        print(f"   响应内容: {res.text[:200]}") # 只看前200字符
        
        # 解析 XML 获取 Group ID
        group_id = None
        if res.status_code == 200:
            try:
                root = ET.fromstring(res.text)
                # v1 成功通常返回 <result><response><resourceid>...</resourceid></response></result>
                # 或者 <AppManager-Response><result><resourceid>...</resourceid></result></AppManager-Response>
                for elem in root.iter():
                    if 'resourceid' in elem.tag.lower():
                        group_id = elem.text
                        break
            except:
                pass
                
        if group_id:
            print(f"✅ 组 '{group_name}' 创建成功! ID: {group_id}")
        else:
            print("⚠️ 组可能已存在或创建失败。尝试通过 ListMonitor 查找 ID...")
            
            # --- 步骤 B: 查找组 ID (如果创建没返回) ---
            list_url = f"{base_url}/ListMonitor"
            list_params = {"apikey": DEFAULT_API_KEY, "type": "MonitorGroup"} # v1 use 'MonitorGroup' type
            r2 = requests.get(list_url, params=list_params, verify=False)
            
            if r2.status_code == 200:
                try:
                    root = ET.fromstring(r2.text)
                    for monitor in root.findall(".//Monitor"):
                        # 查找 DisplayName 属性
                        if monitor.get('DISPLAYNAME') == group_name:
                             group_id = monitor.get('RESOURCEID')
                             break
                except:
                    pass
            
            if group_id:
                print(f"✅ 找到组 ID: {group_id}")
            else:
                print("❌ 无法获取组 ID。终止。")
                return

        # --- 步骤 C: 关联资源到组 ---
        # API: AssociateMonitorToGroup (或者在 v1 中可能是 AddMonitor 的变体)
        # 我们先试 AssociateMonitorToGroup
        assoc_url = f"{base_url}/AssociateMonitorToGroup"
        assoc_params = {
            "apikey": DEFAULT_API_KEY,
            "groupid": group_id,
            "resourceid": target_id
        }
        
        print(f"2. 关联资源 ({target_id}) 到组 ({group_id})...")
        r3 = requests.get(assoc_url, params=assoc_params, verify=False)
        print(f"   HTTP 状态码: {r3.status_code}")
        print(f"   响应内容: {r3.text[:200]}")
        
        if "success" in r3.text.lower():
             print("✅ 关联成功！")
        else:
             print("⚠️ 关联可能失败，请检查响应。")

    except Exception as e:
        print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    # 目标：192.168.130.45 (10113062)
    manage_group_v1("10113062")
