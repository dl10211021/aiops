import requests

# 配置 Prometheus 地址
PROMETHEUS_HOST = "192.168.130.45"
PROMETHEUS_PORT = 9090
BASE_URL = f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}"

def query(promql):
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/query", params={"query": promql}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("result", [])
    except:
        return []
    return []

def check_idrac_status():
    print(f"正在查询 Prometheus ({BASE_URL}) 中的 iDRAC/IPMI 监控数据...")
    
    # 1. 查找是否有 iDRAC 或 IPMI 相关的 Job
    # 我们查询 up 指标，并按 job 分组，看看有哪些 job
    targets = query("up")
    idrac_jobs = set()
    idrac_targets = []
    
    for t in targets:
        job = t["metric"].get("job", "")
        if "idrac" in job.lower() or "ipmi" in job.lower() or "hardware" in job.lower():
            idrac_jobs.add(job)
            idrac_targets.append(t)

    if not idrac_jobs:
        print("❌ 未在 Prometheus 中发现明确标记为 'idrac', 'ipmi' 或 'hardware' 的监控任务。")
        print("   (可能使用了自定义 Job 名称，或尚未接入带外监控)")
    else:
        print(f"✅ 发现 {len(idrac_jobs)} 个硬件监控任务: {', '.join(idrac_jobs)}")
        
        # 2. 检查这些 targets 的存活状态
        down_cnt = 0
        for t in idrac_targets:
            instance = t["metric"].get("instance", "unknown")
            job = t["metric"].get("job", "")
            value = t["value"][1]
            if value != "1":
                down_cnt += 1
                print(f"⚠️  [DOWN] {instance} (Job: {job}) 无法连接!")
        
        if down_cnt == 0:
            print(f"   所有 {len(idrac_targets)} 个带外监控节点网络均正常 (UP)。")

    # 3. 尝试查询具体的硬件健康指标 (Dell iDRAC 通常会有 idrac_system_health_status)
    print("\n正在查询硬件健康指标 (idrac_system_health_status)...")
    health_metrics = query("idrac_system_health_status")
    
    if health_metrics:
        abnormal_cnt = 0
        for m in health_metrics:
            # 通常 3=OK, 4=Warning, 5=Critical (具体视 exporter 而定，这里假设非 3 为异常)
            # 或者有些是 0=OK. 这里打印出来让用户判断。
            val = float(m["value"][1])
            instance = m["metric"].get("instance", "")
            if val != 3: # 假设 3 是 OK (常见的 Dell OID 映射)
                abnormal_cnt += 1
                print(f"⚠️  [异常] {instance}: 系统健康状态值 = {val}")
        
        if abnormal_cnt == 0:
            print("✅ 所有受控 iDRAC 的系统健康状态指标均为正常 (值=3)。")
    else:
        print("ℹ️  未找到 'idrac_system_health_status' 指标。尝试查询 'ipmi_up'...")
        ipmi_up = query("ipmi_up == 0")
        if ipmi_up:
            for m in ipmi_up:
                 print(f"⚠️  [DOWN] IPMI 接口不可达: {m['metric'].get('instance')}")
        else:
             print("   (未找到相关硬件指标)")

if __name__ == "__main__":
    check_idrac_status()
