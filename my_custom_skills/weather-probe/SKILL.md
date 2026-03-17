---
name: Weather Probe (环境气象探针)
description: 用于绕过内置 web_search 搜索引擎的网络阻断，直接调用开源气象 API 接口获取目标城市的实时天气和温度。
version: 1.0.0
---
# 环境气象探针 (Weather Probe)

当内置公网搜索失效，但用户需要获取特定城市、机房外部的实时天气与温度时，请使用本技能卡带。

## 🎯 核心能力
利用轻量级的 Python urllib 原生请求直接调用外部气象服务，规避复杂的依赖安装，适合在高度受限的只读或隔离网络环境中使用。

## 🛠️ 使用指南
使用 `local_execute_script` 工具，在挂载的技能目录中调用 `weather.py` 脚本，将城市英文名或拼音作为参数传入。如果不传参数，默认查询 Nanjing。

**示例：**
```bash
python weather.py Nanjing
python weather.py Beijing
```
