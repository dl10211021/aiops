import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def try_move_to_group(server_id="10113062", group_id="10113133"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml/group/move"
    
    # 尝试用 Move API 把服务器移动到组里
    params = {
        "apikey": DEFAULT_API_KEY,
        "haid": server_id,     # 被移动的资源 (服务器)
        "tohaid": group_id     # 目标组
    }
    
    print("--- 尝试使用 'Move Group' API 移动服务器 ---")
    print(f"URL: {base_url}")
    print(f"Moving {server_id} -> {group_id}")
    
    try:
        res = requests.post(base_url, params=params, verify=False)
        
        print(f"HTTP Status: {res.status_code}")
        print(f"Response: {res.text[:300]}")
        
        if "success" in res.text.lower():
            print("✅ 奇迹发生！服务器成功移动到了组里。")
        elif "not a group" in res.text.lower():
            print("❌ 失败：API 识别出这不是一个组。")
            
    except Exception as e:
        print(f"异常: {e}")

if __name__ == "__main__":
    try_move_to_group()
