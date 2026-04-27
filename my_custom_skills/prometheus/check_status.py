# -*- coding: utf-8 -*-
import requests
import json

url = "http://192.168.130.45:9090"

def check_health():
    # 1. Health Check
    health = requests.get(f"{url}/-/healthy").text
    
    # 2. Targets
    try:
        targets_r = requests.get(f"{url}/api/v1/targets", timeout=5)
        targets_data = targets_r.json().get("data", {}).get("activeTargets", [])
        
        down_targets = []
        for t in targets_data:
            if t.get("health") != "up":
                down_targets.append({
                    "job": t.get("labels", {}).get("job"),
                    "instance": t.get("labels", {}).get("instance"),
                    "health": t.get("health"),
                    "error": t.get("lastError", "")
                })
    except Exception as e:
        targets_data = []
        down_targets = []
        error_msg = str(e)

    # 3. CPU & Memory (Top consumers)
    try:
        cpu_r = requests.get(f"{url}/api/v1/query?query=100-(avg(irate(node_cpu_seconds_total{{mode=\"idle\"}}[5m]))*100))", timeout=5)
        cpu_vals = {v["metric"]["instance"]: float(v["value"][1]) for v in cpu_r.json().get("data", {}).get("result", [])}
    except Exception as e:
        cpu_vals = {"error": str(e)}

    try:
        mem_r = requests.get(f"{url}/api/v1/query?query=100*(1-(node_memory_MemFree_bytes+node_memory_Buffers_bytes+node_memory_Cached_bytes)/node_memory_MemTotal_bytes)", timeout=5)
        mem_vals = {v["metric"]["instance"]: float(v["value"][1]) for v in mem_r.json().get("data", {}).get("result", [])}
    except Exception as e:
        mem_vals = {"error": str(e)}

    result = {
        "prometheus_health": health,
        "total_targets": len(targets_data),
        "down_targets": down_targets,
        "cpu_usage_percent": cpu_vals,
        "memory_usage_percent": mem_vals
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    check_health()