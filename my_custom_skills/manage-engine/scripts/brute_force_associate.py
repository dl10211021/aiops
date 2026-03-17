import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def brute_force_associate(group_id="10113133", resource_id="10113062"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml"
    
    # 所有可能的关联路径猜测
    paths = [
        "associatemonitor/group",   # 最合理的反义词
        "associate/group",          # 简写
        "addresource/group",        # 通用术语
        "group/associate",          # 倒装
        "group/addmonitor",         # 倒装2
        "AddMonitorToGroup",        # 驼峰
        "associatemonitortogroup"   # 全小写
    ]
    
    params = {
        "apikey": DEFAULT_API_KEY,
        "haid": group_id,        # 尝试 haid
        "resourceid": resource_id
    }
    
    # 也要尝试 groupid 参数
    params_alt = {
        "apikey": DEFAULT_API_KEY,
        "groupid": group_id,     # 尝试 groupid
        "resourceid": resource_id
    }
    
    print(f"--- 暴力扫描关联接口 (Group: {group_id}, Resource: {resource_id}) ---")
    
    for path in paths:
        url = f"{base_url}/{path}"
        
        # 尝试 haid
        try:
            r1 = requests.post(url, params=params, verify=False)
            if r1.status_code != 404:
                print(f"🎯 命中! URL: {url} (haid)")
                print(f"   Response: {r1.text[:200]}")
                if "success" in r1.text.lower(): return
        except: pass
        
        # 尝试 groupid
        try:
            r2 = requests.post(url, params=params_alt, verify=False)
            if r2.status_code != 404:
                print(f"🎯 命中! URL: {url} (groupid)")
                print(f"   Response: {r2.text[:200]}")
                if "success" in r2.text.lower(): return
        except: pass

    print("🏁 扫描结束。如果没有命中，说明这些路径都不存在。")

if __name__ == "__main__":
    brute_force_associate()
