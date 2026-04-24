import requests
import json

# 配置 Prometheus 地址
PROMETHEUS_HOST = "192.168.130.45"
PROMETHEUS_PORT = 9090
BASE_URL = f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}"

def check_alerts():
    print(f"正在连接 Prometheus: {BASE_URL} ...")
    try:
        # 设置较短的超时时间
        resp = requests.get(f"{BASE_URL}/api/v1/alerts", timeout=5)
        
        if resp.status_code != 200:
            print(f"❌ 请求失败，HTTP 状态码: {resp.status_code}")
            return
        
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"❌ 返回内容不是有效的 JSON: {resp.text[:100]}")
            return

        if data.get("status") != "success":
            print(f"❌ API 返回状态错误: {data.get('status')}")
            return

        alerts = data.get("data", {}).get("alerts", [])
        
        # 筛选正在触发的告警 (firing)
        firing_alerts = [a for a in alerts if a.get("state") == "firing"]
        
        if not firing_alerts:
            print("✅ 当前系统健康，无活跃告警 (No firing alerts).")
        else:
            print(f"⚠️  发现 {len(firing_alerts)} 个活跃告警:")
            print("=" * 50)
            for idx, alert in enumerate(firing_alerts, 1):
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})
                
                # 提取关键字段
                name = labels.get("alertname", "Unknown Alert")
                severity = labels.get("severity", "unknown")
                instance = labels.get("instance", "N/A")
                summary = annotations.get("summary", "")
                description = annotations.get("description", "")
                
                # 打印告警详情
                print(f"{idx}. [{severity.upper()}] {name}")
                if instance != "N/A":
                    print(f"   来源实例: {instance}")
                if summary:
                    print(f"   摘要: {summary}")
                if description:
                    print(f"   详情: {description}")
                print("-" * 50)

    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器 {BASE_URL}")
        print("   建议排查: 1. 目标 IP/端口是否开放  2. 防火墙策略  3. VPN/网络连通性")
    except requests.exceptions.Timeout:
        print(f"❌ 连接超时 ({BASE_URL})")
    except Exception as e:
        print(f"❌ 发生未预期的错误: {str(e)}")

if __name__ == "__main__":
    check_alerts()
