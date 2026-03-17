# OpsCore Custom Skills 编写指南

这就是你的“超级卡带商店”。你可以随时在这个目录下新建 `.py` 文件来扩展 AI 运维平台的能力。

### 第一步：编写技能代码 (以一个查天气/IP属地的 API 技能为例)

在 `skills/` 下新建一个 `my_custom_skill.py`:

```python
import json
import urllib.request
from typing import Dict, Any, List
from skills.base import BaseSkillProvider

class AwesomeIPLookupSkill(BaseSkillProvider):
    """【黑客帝国】获取 IP 地址的地理位置信息"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "lookup_ip_location",
                    "description": "当用户问某台服务器或 IP 在哪个城市/国家时，调用此工具获取属地信息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ip_address": {"type": "string", "description": "要查询的 IPv4 地址"}
                        },
                        "required": ["ip_address"]
                    }
                }
            }
        ]
        
    def execute(self, tool_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> str:
        # 这里你可以执行你原来的 Python 脚本！
        if tool_name == "lookup_ip_location":
            ip = args.get("ip_address")
            try:
                # 调用一个免费的外网 API 查 IP
                req = urllib.request.Request(f"http://ip-api.com/json/{ip}?lang=zh-CN", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    return json.dumps({"status": "SUCCESS", "location": f"{data.get('country')} - {data.get('city')} - {data.get('isp')}"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        return '{"error": "Unknown tool"}'
```

### 第二步：注册你的技能卡带

去打开 `core/dispatcher.py` 文件，找到 `__init__` 函数。
把你刚写的卡带插进去：

```python
from skills.my_custom_skill import AwesomeIPLookupSkill

class SkillDispatcher:
    def __init__(self):
        self.providers = {
            "linux_basic": LinuxSkillProvider(),
            "mysql_dba": None,
            # 插上你自己的卡带！
            "awesome_ip": AwesomeIPLookupSkill() 
        }
```

### 第三步：去页面上勾选它！
现在，你只需要刷新前端页面。点击左上角的 `+` 连接服务器。
你会发现列表里多了一个：`[ ] Awesome Ip` 的复选框！
勾选它，连上机器。然后对 AI 说：“帮我看看我现在的出口 IP 是哪里？”

AI 就会自动调起你写的 Python 脚本，瞬间完成高阶任务！
