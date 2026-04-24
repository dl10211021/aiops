import requests

# 配置 Prometheus 地址
PROMETHEUS_HOST = "192.168.130.45"
PROMETHEUS_PORT = 9090
BASE_URL = f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}"

def query(promql):
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/query", params={"query": promql}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("result", [])
    except Exception as e:
        print(f"Query error: {e}")
        return []
    return []

def check_bmc_status():
    print(f"正在深度扫描 Prometheus ({BASE_URL}) 中的 BMC/IPMI 监控数据...")
    
    # 1. 宽泛搜索：列出所有 Job 名称，寻找包含 bmc, ipmi, hardware, redfish 的 Job
    print("\n[Step 1] 正在搜索监控 Job...")
    try:
        # 获取所有 job 名称
        resp = requests.get(f"{BASE_URL}/api/v1/label/job/values", timeout=5)
        if resp.status_code == 200:
            all_jobs = resp.json().get("data", [])
            target_jobs = [j for j in all_jobs if any(k in j.lower() for k in ['bmc', 'ipmi', 'hardware', 'oob', 'redfish', 'server'])]
            
            if target_jobs:
                print(f"✅ 发现疑似 BMC/硬件相关的 Job: {', '.join(target_jobs)}")
                
                # 针对发现的 Job 检查 up 状态
                for job in target_jobs:
                    print(f"   正在检查 Job: {job} ...")
                    up_targets = query(f"up{{job='{job}'}}")
                    down_count = 0
                    total_count = len(up_targets)
                    
                    for t in up_targets:
                        instance = t['metric'].get('instance')
                        val = t['value'][1]
                        if val != '1':
                            down_count += 1
                            print(f"   ⚠️  [BMC DOWN] {instance} 无法连接 (监控采集失败)")
                    
                    if total_count > 0 and down_count == 0:
                        print(f"     - 所有 {total_count} 个目标采集正常。")
            else:
                print("❌ 未发现名称中包含 bmc/ipmi/hardware 的 Job。")
        else:
            print("无法获取 Label values。")
            
    except Exception as e:
        print(f"Error fetching jobs: {e}")

    # 2. 直接查询 IPMI 核心指标 (无论 Job 叫什么)
    print("\n[Step 2] 正在扫描通用 IPMI 指标 (ipmi_up, ipmi_sensor_state)...")
    
    # 2.1 检查 BMC 是否在线 (ipmi_up)
    # 有些 exporter 使用 ipmi_up 指标来表示是否连通 BMC
    ipmi_ups = query("ipmi_up")
    if ipmi_ups:
        print(f"✅ 发现 {len(ipmi_ups)} 个 BMC 监控目标 (指标: ipmi_up)。")
        for t in ipmi_ups:
            instance = t['metric'].get('instance')
            val = t['value'][1]
            if val == '0':
                print(f"⚠️  [BMC 离线] {instance} - ipmi_up 为 0 (无法连接到 BMC)")
    else:
        print("ℹ️  未找到 'ipmi_up' 指标。")

    # 2.2 检查传感器状态 (ipmi_sensor_state)
    # 通常 0=OK, 1=Warning, 2=Critical (具体看 exporter 实现，这里列出非0的)
    sensors = query("ipmi_sensor_state != 0") # 假设 0 是正常
    if sensors:
        print(f"\n⚠️  发现 {len(sensors)} 个传感器异常:")
        for s in sensors:
            instance = s['metric'].get('instance')
            sensor_name = s['metric'].get('name', 'unknown')
            sensor_type = s['metric'].get('type', 'unknown')
            val = s['value'][1]
            print(f"   - [{instance}] 传感器: {sensor_name} ({sensor_type}) 状态值: {val}")
    else:
        # 尝试另一种常见的 metric: ipmi_sel_logs_count (系统事件日志)
        sel_logs = query("ipmi_sel_logs_count > 0")
        if sel_logs:
             print("\n⚠️  发现 SEL 日志非空 (可能有硬件历史报错):")
             for l in sel_logs:
                 instance = l['metric'].get('instance')
                 val = l['value'][1]
                 print(f"   - [{instance}] SEL 日志数: {val}")

    # 3. 针对之前宕机的业务 IP，尝试反查是否有对应的 BMC
    # 假设 BMC IP 和业务 IP 有某种关联，或者 exporter 的 instance 就是业务 IP
    down_ips = ["192.168.122.237", "192.168.10.102", "192.168.129.220"]
    print(f"\n[Step 3] 正在尝试关联故障业务 IP ({', '.join(down_ips)}) 到 BMC...")
    
    # 模糊匹配这些 IP 出现在任何指标中
    for ip in down_ips:
        # 查询该 IP 是否作为 instance 或其他 label 出现
        # 这里只查 up 指标，看是否有相关的 bmc job
        res = query(f"up{{instance=~'.*{ip}.*', job=~'.*bmc.*|.*ipmi.*'}}")
        if res:
            for r in res:
                job = r['metric'].get('job')
                instance = r['metric'].get('instance')
                status = "UP" if r['value'][1] == '1' else "DOWN"
                print(f"   -> 找到关联监控: IP {ip} 对应 BMC 实例 {instance} (Job: {job}) -> 状态: {status}")
        else:
            print(f"   -> 未找到 IP {ip} 的明确 BMC 监控记录。")

if __name__ == "__main__":
    check_bmc_status()
