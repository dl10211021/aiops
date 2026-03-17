---
name: manage-engine
description: 卓豪 (ManageEngine) 监控专家。提供 OpManager 和 Applications Manager 的 API 自动化、日志分析、自动巡检及故障诊断服务。
---

# 卓豪 (ManageEngine) 监控专家

该 Skill 专门用于协助管理和自动化 **卓豪 (ManageEngine)** 系列产品，特别是 **Applications Manager (AppManager)** 和 **OpManager**。

## 🎯 核心能力

### 1. API 自动化与管理
使用 `scripts/manage_engine_api.py` 核心库与卓豪 API 交互。配置现在通过 `config.json` 管理。
- **获取告警**: `client.list_alarms(type='critical')` - 自动抓取严重告警。
- **获取数据**: `client.get_monitor_data('10030298')` - 抓取 CPU、内存、磁盘等详细指标。
- **添加监控**: 使用 `scripts/add_linux.py` 一键添加 Linux 服务器（已调优参数）。
- **删除监控**: `client.delete_monitor(resource_id)` - 删除指定资源的监控。
- **状态管理**: `client.manage_monitor(resource_id, 'unmanage')` - 暂停/恢复监控轮询。
- **维护计划**: 使用 `scripts/manage_maintenance.py` 创建自动停机维护任务。

**使用示例:**
```python
from scripts.manage_engine_api import AppManagerClient
# 自动从 config.json 加载配置
client = AppManagerClient() 
data = client.get_monitor_data("10030298")
```

### 2. 容量规划与预测 (Capacity Planning)
使用 `scripts/capacity_planner.py` 生成未来 7 天的容量预测报告（HTML）。
- **核心功能**: 预测 CPU、内存、磁盘的增长趋势，识别 7 天内即将耗尽的资源。
- **全平台兼容**: 支持 Windows 2003/2008/2012/2016/2019/2022、Windows 10/11、Linux。
- **智能降噪**: 自动剔除 ISO 镜像挂载、系统临时目录等无效告警。
- **业务分级**: 自动识别 MES/ERP/DB 等核心业务，并在报告中高亮显示。

**一键生成汇报级报告:**
```bash
# 生成全量报告 (默认 forecast.csv -> capacity_report.html)
python scripts/capacity_planner.py
```

**单机诊断 (快速检查):**
```bash
# 检查特定 IP 的未来趋势
python scripts/check_server_capacity.py 192.168.42.159
```

### 3. 自动化添加监控 (Linux)
**单台服务器添加:**
使用 `scripts/add_linux.py` 快速纳管新服务器。支持自定义显示名称和自动关联资源组。
```bash
# 基本用法：仅 IP、用户、密码 (默认名称 Linux_IP)
python scripts/add_linux.py 192.168.130.45 root password

# 进阶用法：指定显示名称和业务组 ID
python scripts/add_linux.py 192.168.130.45 root password --name "Web-Server-01" --group 10113133
```

**批量导入 (CSV):**
使用 `scripts/batch_add_linux.py` 从 CSV 文件批量添加多台服务器。
1. 编辑 `scripts/servers.csv` 文件 (Excel 打开)，填入服务器列表。
2. **自定义分组**: 在 `Group ID` 列填入目标监控组的 ID。
3. 运行脚本:
```bash
python scripts/batch_add_linux.py
```

### 4. 资源查找与管理
**查找资源 (Monitor/Group):**
使用 `scripts/find_resource.py` 快速搜索监控对象或资源组 ID。
```bash
# 搜索 IP 或名称
python scripts/find_resource.py "192.168.130.45"

# 搜索资源组 (如查找 AD 相关组的 ID)
python scripts/find_resource.py "ADTest" --type group
```

**按指标查找 (CPU/内存/磁盘):**
使用 `scripts/find_resources.py` 查找超过特定阈值的资源。
```bash
# 查找 CPU > 80% 的资源
python scripts/find_resources.py --metric cpu --threshold 80

# 查找内存 > 90% 的 Linux 服务器
python scripts/find_resources.py --metric memory --threshold 90 --type Linux
```

**删除监控资源:**
使用 `scripts/delete_monitor.py` 删除不需要的监控资源。
```bash
# 通过 IP 地址或显示名称删除（会提示确认）
python scripts/delete_monitor.py 192.168.130.45

# 直接通过资源 ID 删除
python scripts/delete_monitor.py 10113198 --id
```

### 5. 资源配置 (Thresholds & Actions)
**查看配置选项:**
```bash
# 查看所有告警阈值模板
python scripts/list_thresholds.py

# 查看所有告警动作 (邮件/微信等)
python scripts/list_actions.py
```

### 6. 深度分析与巡检

**一、单机诊断任务 (Single Task Analysis)**
针对单个服务器或应用进行深度体检，包含实时性能、关键指标及最近一周的告警历史。
使用 `scripts/analyze_resource.py` 脚本。

```bash
# 基础用法：支持 IP、名称或资源 ID
python scripts/analyze_resource.py 192.168.130.45
```

**二、批量巡检任务 (Batch/Global Inspection)**
对全网资源进行健康状况扫描，快速发现宕机、告警或状态未知的节点。
使用 `scripts/health_report.py` 脚本。

```bash
# 默认模式：显示全局概览 + 严重/警告资源清单
python scripts/health_report.py

# 专项检查：仅列出“未知”状态的资源
python scripts/health_report.py --status unknown

# 详细模式：列出所有非正常 (Non-Clear) 资源
python scripts/health_report.py -v
```

## 🛠️ 常用脚本清单
| 脚本 | 功能 | 备注 |
| :--- | :--- | :--- |
| `capacity_planner.py` | **容量规划主程序** | 一键生成预测报告 (HTML) |
| `check_server_capacity.py` | **单机预测工具** | 快速检查单台机器的未来趋势 |
| `forecast_capacity.py` | 容量预测核心 | 生成 CSV 数据 (全兼容) |
| `generate_forecast_report.py` | 报告生成器 | CSV -> HTML (高管汇报版) |
| `add_linux.py` | 添加 Linux 主机 | 支持自定义名称和分组 |
| `add_process.py` | 添加进程监控 | 支持自动关联告警动作 |
| `configure_process_alarm.py` | 配置进程告警 | 修复进程可用性告警关联 |
| `manage_maintenance.py` | 停机维护与状态管理 | 支持创建计划维护和 Manage/UnManage |
| `find_resource.py` | 查找资源 ID | 支持 Monitor 和 Group |
| `find_resources.py` | 查找高负载资源 | 支持 CPU/内存/磁盘阈值过滤 |
| `analyze_resource.py` | 资源深度分析 | 包含状态、指标、告警历史 |
| `configure_resource.py` | 配置阈值和动作 | 支持 CPU/Mem/Disk/Ping |
| `manage_engine_api.py` | 核心 API 库 | 自动加载 config.json |

## 🛠️ 环境配置
配置已移至 `config.json` 文件：
```json
{
  "url": "https://192.168.129.132:8443",
  "api_key": "YOUR_API_KEY"
}
```

## 💡 最佳实践
- **每日巡检**: 建议每天运行一次 `health_report.py`，重点关注 MES、ERP 等核心业务节点的健康度。
- **每周规划**: 每周运行一次 `capacity_planner.py`，根据 HTML 报告提前处理即将耗尽的磁盘空间。
- **故障排查**: 当发现资源变红时，先用 `scripts/inspector.py` 获取详细报错，再决定是否登录服务器处理。

## 📚 相关文档
- **[API 参考文档](API_REFERENCE.md)**: 完整的 REST API 使用指南，包含所有端点、参数说明和示例代码。
