from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def linux_dashboard(target_id):
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(target_id)
    
    if data and 'response' in data and 'result' in data['response']:
        res = data['response']['result'][0]
        
        print("\n--- 卓豪 Linux 实时看板 (资源ID: " + target_id + ") ---")
        
        metrics = {
            "DISPLAYNAME": "主机名称",
            "CPUUTIL": "CPU 使用率 (%)",
            "MEMUTIL": "内存使用率 (%)",
            "RESPONSETIME": "响应时间 (ms)",
            "AVAILABILITYSTATUS": "在线状态"
        }
        
        for k, label in metrics.items():
            val = res.get(k, "未知")
            if val == "-1" or val == "N/A": val = "数据采集中..."
            # 简单的状态汉化
            if k == "AVAILABILITYSTATUS" and str(val).lower() == "up":
                val = "✅ 正常 (UP)"
            elif k == "AVAILABILITYSTATUS" and str(val).lower() == "down":
                val = "❌ 宕机 (DOWN)"
                
            print(label + ": " + str(val))
        print("-" * 45)

if __name__ == "__main__":
    # 1. 尝试查看新加的机器
    print("正在连接卓豪服务器查询...")
    linux_dashboard("10113062")
    
    # 2. 同时展示一台已有的正常机器的数据
    print("\nCHECKING EXISTING SERVER (For comparison)...")
    linux_dashboard("10037234")