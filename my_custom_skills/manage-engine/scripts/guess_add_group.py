import requests
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def try_add_monitor_to_group(group_name="test", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml"
    
    # 猜测的 endpoint: addmonitor/group
    # 基于 removemonitor/group 的反向推导
    url = f"{base_url}/addmonitor/group"
    
    params = {
        "apikey": DEFAULT_API_KEY,
        "mgname": group_name,      # 使用组名，因为我们可能还没有 ID
        "resourceid": resource_id
    }
    
    print(f"--- 尝试把 {resource_id} 加入组 '{group_name}' ---")
    print(f"URL: {url}")
    
    try:
        res = requests.post(url, params=params, verify=False)
        print(f"HTTP 状态: {res.status_code}")
        print(f"响应内容: {res.text[:300]}")
        
        if "success" in res.text.lower() or "associated" in res.text.lower():
            print("✅ 成功关联！")
        else:
            print("❌ 关联失败。")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    try_add_monitor_to_group("test", "10113062")
