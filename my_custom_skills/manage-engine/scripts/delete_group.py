import requests
import urllib3
from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def delete_group(group_id="10113133", group_name="ADTest"):
    base_url = DEFAULT_URL.rstrip('/') + "/AppManager/xml"
    
    print(f"--- 尝试删除组: {group_name} ({group_id}) ---")
    
    # 方案 1: DeleteMonitorGroup (专门接口)
    url_1 = f"{base_url}/DeleteMonitorGroup"
    params_1 = {
        "apikey": DEFAULT_API_KEY,
        "groupid": group_id
    }
    
    try:
        r1 = requests.post(url_1, params=params_1, verify=False)
        if r1.status_code != 404:
            print(f"🎯 尝试 DeleteMonitorGroup: {r1.status_code}")
            print(f"   响应: {r1.text[:200]}")
            if "success" in r1.text.lower() or "deleted" in r1.text.lower():
                print("✅ 删除成功！")
                return
    except: pass

    # 方案 2: RemoveMonitor (通用删除)
    url_2 = f"{base_url}/removemonitor"
    params_2 = {
        "apikey": DEFAULT_API_KEY,
        "resourceid": group_id
    }
    
    try:
        r2 = requests.post(url_2, params=params_2, verify=False)
        if r2.status_code != 404:
            print(f"🎯 尝试 RemoveMonitor: {r2.status_code}")
            print(f"   响应: {r2.text[:200]}")
            if "success" in r2.text.lower() or "deleted" in r2.text.lower():
                print("✅ 删除成功！")
                return
    except: pass

    print("🏁 删除尝试结束。")

if __name__ == "__main__":
    delete_group()
