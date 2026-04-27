import requests, json
try:
    t = requests.get("http://192.168.130.45:9090/api/v1/targets", timeout=5).json().get("data",{}).get("activeTargets",[])
    d = [x for x in t if x.get("health")!="up"]
    print(f"Total: {len(t)}, Down: {len(d)}")
    print(json.dumps(d, indent=2))
except Exception as e:
    print(e)