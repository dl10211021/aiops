import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def final_associate_attempt(group_id="10113133", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml"
    
    # 针对 Associate Monitor to Monitor Group 的终极 URL 猜测
    candidates = [
        "AssociateMonitor",           # 最可能：动作动词
        "associatemonitor",           # 全小写
        "AssociateMonitorToGroup",    # 标准命名 (已试过 404, 但再确认一次)
        "AddMonitorToGroup"           # 另一种可能
    ]
    
    params = {
        "apikey": DEFAULT_API_KEY,
        "resourceid": resource_id,
        "groupid": group_id
    }
    
    # 备用参数：有些旧版本用 haid 代表组 ID
    params_legacy = {
        "apikey": DEFAULT_API_KEY,
        "resourceid": resource_id,
        "haid": group_id
    }

    print(f"--- 尝试将 {resource_id} 关联到组 {group_id} ---")
    
    for endpoint in candidates:
        url = f"{base_url}/{endpoint}"
        
        # 尝试标准参数 (groupid)
        try:
            r1 = requests.post(url, params=params, verify=False)
            if r1.status_code != 404:
                print(f"🎯 命中! URL: {url} (groupid)")
                print(f"   Response: {r1.text[:200]}")
                if "success" in r1.text.lower(): return
        except: pass
        
        # 尝试旧版参数 (haid)
        try:
            r2 = requests.post(url, params=params_legacy, verify=False)
            if r2.status_code != 404:
                print(f"🎯 命中! URL: {url} (haid)")
                print(f"   Response: {r2.text[:200]}")
                if "success" in r2.text.lower(): return
        except: pass

    print("🏁 扫描结束。")

if __name__ == "__main__":
    final_associate_attempt()
