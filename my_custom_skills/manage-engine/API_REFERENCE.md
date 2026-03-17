# ManageEngine Applications Manager REST API 参考文档

本文档整理了 ManageEngine Applications Manager 的 REST API 使用方法和最佳实践。

## 📋 目录

1. [认证方式](#认证方式)
2. [API 基础](#api-基础)
3. [监控管理 API](#监控管理-api)
4. [告警 API](#告警-api)
5. [性能数据 API](#性能数据-api)
6. [分组管理 API](#分组管理-api)
7. [阈值管理 API](#阈值管理-api)
8. [维护与状态 API](#维护与状态-api)
9. [错误处理](#错误处理)
10. [最佳实践](#最佳实践)

---

## 认证方式

所有 API 请求都需要包含 `apikey` 参数进行认证。

### 获取 API Key

1. 登录 Applications Manager Web 界面
2. 点击右上角的 Profile 图标
3. 点击 Edit → 'Click here' 查看 REST API key
4. 复制生成的 API key

### 示例
```python
DEFAULT_API_KEY = "9f6f30a5b2163fd920fea01e3d5d411f"
```

---

## API 基础

### 基础 URL 格式

```
https://<host>:<port>/AppManager/<format>/<endpoint>
```

- `<host>`: 服务器地址（如 `192.168.129.132`）
- `<port>`: 端口号（默认 `8443` HTTPS 或 `9090` HTTP）
- `<format>`: 响应格式 (`json` 或 `xml`)
- `<endpoint>`: API 端点名称

### 请求方法

- **GET**: 查询数据（ListMonitor, GetMonitorData 等）
- **POST**: 修改数据（AddMonitor, DeleteMonitor 等）

### Python 客户端示例

```python
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
```

---

## 监控管理 API

### 1. 列出所有监控 (ListMonitor)

获取所有监控资源的列表。

**端点**: `ListMonitor`
**方法**: `GET`
**格式**: `json` 或 `xml`

**参数**:
- `type` (可选): 监控类型过滤
  - `all`: 所有监控（默认）
  - `servers`: 仅服务器监控
  - `Linux`: Linux 服务器
  - `Windows`: Windows 服务器
- `groupid` (可选): 按监控组 ID 过滤
- `resourceid` (可选): 查询特定资源 ID

**Python 示例**:
```python
# 获取所有监控
all_monitors = client.list_monitors()

# 按类型过滤
linux_servers = client.list_monitors(type="Linux")

# 按组过滤
group_monitors = client.list_monitors(groupid="10113133")
```

**cURL 示例**:
```bash
curl "https://192.168.129.132:8443/AppManager/json/ListMonitor?apikey=YOUR_API_KEY&type=all"
```

**响应结构**:
```json
{
  "response-code": "4000",
  "response": {
    "result": [
      {
        "RESOURCEID": "10113198",
        "DISPLAYNAME": "Linux_192.168.130.45",
        "TYPESHORTNAME": "Linux",
        "HOSTIP": "192.168.130.45",
        "HOSTNAME": "192.168.130.45",
        "HEALTHSTATUS": "clear",
        "AVAILABILITYSTATUS": "up",
        "HEALTHMESSAGE": "Health is clear...",
        "PORT": "22",
        "LAST_POLLED_TIME": "1770614009321"
      }
    ]
  }
}
```

---

### 2. 添加监控 (AddMonitor)

添加新的监控资源。

**端点**: `AddMonitor`
**方法**: `POST`
**格式**: `json` 或 `xml`

#### 2.1 添加 Linux 服务器监控

**必需参数**:
- `type`: `servers`
- `displayname`: 显示名称
- `host`: 主机 IP 地址
- `os`: `Linux`
- `mode`: `SSH`
- `username`: SSH 用户名
- `password`: SSH 密码
- `snmptelnetport`: SSH 端口（默认 `22`）

**可选参数**:
- `pollInterval`: 轮询间隔（分钟，默认 `5`）
- `timeout`: 超时时间（秒，默认 `10`）
- `prompt`: Shell 提示符（默认 `#`）
- `addgivenname`: 使用给定的名称（`true` 或 `false`）
- `addToGroup`: 是否加入监控组（`true` 或 `false`）
- `groupID`: 监控组 ID（需配合 `addToGroup=true`）

**Python 示例**:
```python
# 添加 Linux 服务器
result = client.add_linux_monitor(
    ip="192.168.1.100",
    user="root",
    password="password123",
    display_name="Linux_192.168.1.100",
    group_id="10113133"  # 可选：加入指定组
)
```

**cURL 示例**:
```bash
curl -d "apikey=YOUR_API_KEY&type=servers&displayname=Linux_192.168.1.100&host=192.168.1.100&snmptelnetport=22&os=Linux&mode=SSH&username=root&password=password123&pollInterval=5&prompt=#&timeout=10&addgivenname=true&addToGroup=true&groupID=10113133" \
"https://192.168.129.132:8443/AppManager/json/AddMonitor"
```

#### 2.2 添加 Windows 服务器监控

**必需参数**:
- `type`: `servers`
- `displayname`: 显示名称
- `host`: 主机 IP 地址
- `os`: `Windows`
- `mode`: `WMI`
- `username`: Windows 用户名（格式：`DOMAIN\username` 或 `.\username`）
- `password`: Windows 密码

**Python 示例**:
```python
result = client.add_monitor(
    display_name="Windows_192.168.1.200",
    type_name="servers",
    host="192.168.1.200",
    os="Windows",
    mode="WMI",
    username=".\\Administrator",
    password="password123",
    pollInterval="5"
)
```

---

### 3. 删除监控 (DeleteMonitor)

删除指定的监控资源。

**端点**: `DeleteMonitor`
**方法**: `POST`
**格式**: `json` 或 `xml`

**参数**:
- `resourceid` (必需): 要删除的资源 ID

**Python 示例**:
```python
# 删除监控
result = client.delete_monitor("10113198")
```

**cURL 示例**:
```bash
curl -d "apikey=YOUR_API_KEY&resourceid=10113198" \
"https://192.168.129.132:8443/AppManager/json/DeleteMonitor"
```

**响应示例**:
```json
{
  "response-code": "4000",
  "response": {
    "result": [
      {
        "message": "成功删除了监控器"
      }
    ],
    "uri": "/AppManager/json/DeleteMonitor"
  }
}
```

---

### 4. 获取子监控 (GetChildMonitors)

获取监控组下的所有子监控。

**端点**: `GetChildMonitors`
**方法**: `GET`

**参数**:
- `resourceid` (必需): 监控组的资源 ID

**Python 示例**:
```python
children = client.get_child_monitors("10113133")
```

---

## 告警 API

### 列出告警 (ListAlarms)

获取当前的告警列表。

**端点**: `ListAlarms`
**方法**: `GET`

**参数**:
- `type` (可选): 告警类型过滤
  - `all`: 所有告警（默认）
  - `critical`: 严重告警
  - `warning`: 警告告警
  - `clear`: 已清除的告警

**Python 示例**:
```python
# 获取所有严重告警
critical_alarms = client.list_alarms(type="critical")

# 获取所有告警
all_alarms = client.list_alarms(type="all")
```

**cURL 示例**:
```bash
curl "https://192.168.129.132:8443/AppManager/json/ListAlarms?apikey=YOUR_API_KEY&type=critical"
```

**响应结构**:
```json
{
  "response-code": "4000",
  "response": {
    "result": [
      {
        "RESOURCEID": "10030298",
        "DISPLAYNAME": "Server01",
        "SEVERITY": "Critical",
        "MESSAGE": "CPU usage exceeds 90%",
        "ALARMTIME": "1770612654488",
        "ATTRIBUTENAME": "CPU Utilization"
      }
    ]
  }
}
```

---

## 性能数据 API

### 获取监控数据 (GetMonitorData)

获取指定资源的最新性能数据。

**端点**: `GetMonitorData`
**方法**: `GET`

**参数**:
- `resourceid` (必需): 资源 ID

**Python 示例**:
```python
# 获取服务器性能数据
data = client.get_monitor_data("10030298")
```

**cURL 示例**:
```bash
curl "https://192.168.129.132:8443/AppManager/json/GetMonitorData?apikey=YOUR_API_KEY&resourceid=10030298"
```

**响应示例**:
```json
{
  "response-code": "4000",
  "response": {
    "result": {
      "RESOURCEID": "10030298",
      "DISPLAYNAME": "Linux_Server01",
      "attributes": [
        {
          "ATTRIBUTEID": "402",
          "ATTRIBUTENAME": "CPU Utilization",
          "VALUE": "45.2",
          "UNIT": "%"
        },
        {
          "ATTRIBUTEID": "403",
          "ATTRIBUTENAME": "Memory Utilization",
          "VALUE": "62.8",
          "UNIT": "%"
        }
      ]
    }
  }
}
```

---

## 分组管理 API

### 1. 创建监控组 (AddMonitorGroup)

创建新的监控组。

**端点**: `AddMonitorGroup`
**方法**: `POST`
**格式**: `xml` (推荐)

**参数**:
- `name` (必需): 组名称
- `grouptype` (必需): 组类型，固定为 `monitorgroup`
- `description` (可选): 组描述

**Python 示例**:
```python
result = client.create_monitor_group(
    group_name="ADTest",
    description="Active Directory Test Group"
)
```

**cURL 示例**:
```bash
curl -d "apikey=YOUR_API_KEY&name=ADTest&grouptype=monitorgroup&description=Test%20Group" \
"https://192.168.129.132:8443/AppManager/xml/AddMonitorGroup"
```

---

### 2. 关联监控到组 (AssociateMonitorToGroup)

将监控资源添加到监控组。

**端点**: `AssociateMonitorToGroup`
**方法**: `POST`

**参数**:
- `groupid` (必需): 监控组 ID
- `resourceid` (必需): 资源 ID（可以是逗号分隔的多个 ID）

**Python 示例**:
```python
# 单个资源
result = client.associate_monitor_to_group("10113133", "10113198")

# 多个资源
result = client.associate_monitor_to_group("10113133", ["10113198", "10113199"])
```

**cURL 示例**:
```bash
curl -d "apikey=YOUR_API_KEY&groupid=10113133&resourceid=10113198,10113199" \
"https://192.168.129.132:8443/AppManager/json/AssociateMonitorToGroup"
```

---

## 阈值管理 API

### 1. 列出阈值配置文件 (ListThresholdProfiles)

获取所有可用的阈值配置文件。

**端点**: `ListThresholdProfiles`
**方法**: `GET`

**Python 示例**:
```python
profiles = client.list_threshold_profiles()
```

---

### 2. 关联阈值配置 (AssociateThresholdProfile)

将阈值配置文件应用到监控资源的特定属性。

**端点**: `AssociateThresholdProfile`
**方法**: `POST`
**格式**: `xml` (推荐)

**参数**:
- `resourceid` (必需): 资源 ID
- `attributeid` (必需): 属性 ID
- `thresholdid` (必需): 阈值配置 ID
- `pollcount` (可选): 轮询次数（默认 `1`）

**Python 示例**:
```python
result = client.associate_threshold_profile(
    resource_id="10030298",
    attribute_id="402",
    profile_id="1000001"
)
```

---

### 3. 配置告警阈值 (configurealarms)

直接配置监控属性的告警阈值，支持单个监控或监控类型的批量配置。

**端点**: `configurealarms`
**方法**: `POST`
**格式**: `xml`
**角色**: 管理员
**参考**: [Configure Alarms API](https://www.manageengine.com/products/applications_manager/help/configure-alarms.html)

#### 3.1 API 语法

```
# 单个监控配置
https://[HOST]:[PORT]/AppManager/xml/configurealarms?apikey=[API Key]&resourceid=[resourceid]&attributeid=[attribute IDs]&thresholdid=[Threshold ID]&criticalactionid=[Action ID]&warningactionid=[Action ID]&clearactionid=[Action ID]&requesttype=[1/2/3/8]&availabilityCriticalPollCount=[count]&availabilityClearPollCount=[count]

# 监控类型模板配置
https://[HOST]:[PORT]/AppManager/xml/configurealarms?apikey=[API Key]&resourceType=[Resource Type]&thresholdid=[Threshold ID]&attributeid=[attribute IDs]&requesttype=[1/2]&overrideConf=[true/false]
```

#### 3.2 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `apikey` | API 密钥 | `9f6f30a5b2163fd920fea01e3d5d411f` |
| `resourceid` / `monitorname` | 资源 ID 或监控名称 | `10000111` |
| `attributeid` | 属性 ID（多个用逗号分隔） | `708` 或 `400,401,53007` |
| `requesttype` | 请求类型 | `1`=保存, `2`=保存并继续, `3`=移除, `8`=删除模板 |

#### 3.3 阈值配置参数

**方式 1: 使用现有阈值模板（推荐）**
| 参数 | 说明 | 示例 |
|------|------|------|
| `thresholdid` / `thresholdname` | 阈值模板 ID 或名称 | `1`, `3` |
| `overrideConf` | 覆盖现有配置 | `true` / `false` |

**方式 2: 自定义阈值值**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `criticalthresholdvalue` | 严重告警阈值 | - |
| `warningthresholdvalue` | 警告告警阈值 | - |
| `infothresholdvalue` | 清除告警阈值 | - |
| `criticalthresholdcondition` | 严重阈值比较条件 | `>`, `<`, `=`, `>=`, `<=` |
| `warningthresholdcondition` | 警告阈值比较条件 | `>`, `<`, `=`, `>=`, `<=` |
| `infothresholdcondition` | 清除阈值比较条件 | `<` |
| `consecutive_criticalpolls` | 连续严重轮询次数 | `2` |
| `consecutive_warningpolls` | 连续警告轮询次数 | `2` |
| `consecutive_clearpolls` | 连续清除轮询次数 | `1` |
| `criticalthresholdmessage` | 严重告警消息 | - |
| `warningthresholdmessage` | 警告告警消息 | - |
| `infothresholdmessage` | 清除告警消息 | - |

#### 3.4 动作关联参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `criticalactionid` / `criticalactionname` | 严重告警动作 ID/名称 | `10000003` |
| `warningactionid` / `warningactionname` | 警告告警动作 ID/名称 | `10000003` |
| `clearactionid` / `clearactionname` | 清除告警动作 ID/名称 | `10000003` |

#### 3.5 轮询计数参数

| 参数 | 说明 | 用途 |
|------|------|------|
| `availabilityCriticalPollCount` | 可用性严重轮询计数 | 连续失败多少次触发严重告警 |
| `availabilityClearPollCount` | 可用性清除轮询计数 | 连续成功多少次清除告警 |

#### 3.6 高级参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `resourceType` | 监控类型（批量配置） | `servers`, `PHP`, `MySQL` |
| `haid` | 监控组 ID | `10000001` |
| `similarmonitors` | 相似监控资源 ID（逗号分隔） | `10001,10002,10003` |
| `removeRCA` | 移除根因分析消息 | `true` / `false` |
| `groupTemplate` | 组模板配置 | `true` / `false` |
| `displayname` | 阈值显示名称 | `Custom CPU Threshold` |
| `type` | 阈值类型 | `1`/`2`=整数, `3`=浮点, `4`=字符串 |
| `description` | 阈值描述 | `High CPU usage threshold` |

#### 3.7 Python 示例

**示例 1: 使用阈值模板（推荐）**
```python
# 应用默认阈值模板
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",      # CPU 利用率
    threshold_id="1",        # 默认模板
    request_type=1,
    override_conf=True
)
```

**示例 2: 配置带动作的告警**
```python
# 配置 CPU 告警并关联微信机器人通知
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    threshold_id="3",
    critical_action_id="10000003",  # 微信机器人动作
    warning_action_id="10000003",
    clear_action_id="10000003",
    availability_critical_poll_count=4,
    availability_clear_poll_count=7,
    request_type=1,
    override_conf=True
)
```

**示例 3: 批量配置多个属性**
```python
# 同时配置 CPU、内存、磁盘告警
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708,685,711",  # CPU, 内存, 磁盘
    threshold_id="1",
    request_type=1,
    override_conf=True
)
```

**示例 4: 自定义阈值**
```python
# 配置自定义 CPU 阈值
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    critical_threshold=95,
    warning_threshold=85,
    info_threshold=70,
    critical_condition=">",
    warning_condition=">",
    info_condition="<",
    consecutive_critical_polls=3,
    consecutive_warning_polls=2,
    critical_message="CPU 使用率严重过高！",
    warning_message="CPU 使用率升高，请关注",
    info_message="CPU 使用率已恢复正常",
    request_type=1,
    override_conf=True
)
```

**示例 5: 监控类型模板**
```python
# 为所有 Linux 服务器应用阈值
result = client.configure_alarm(
    resource_type="servers",
    attribute_id="708",
    threshold_id="1",
    request_type=1,
    override_conf=False  # 不覆盖已配置的监控
)
```

**示例 6: 可用性告警**
```python
# 配置服务器宕机告警
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="700",  # 可用性属性
    threshold_id="1",
    critical_action_id="10000003",
    availability_critical_poll_count=3,  # 连续失败 3 次告警
    availability_clear_poll_count=2,     # 连续成功 2 次清除
    request_type=1,
    override_conf=True
)
```

**示例 7: 移除告警配置**
```python
# 移除 CPU 告警配置
result = client.configure_alarm(
    resource_id="10113263",
    attribute_id="708",
    request_type=3  # 移除配置
)
```

#### 3.8 cURL 示例

```bash
# 使用阈值模板
curl -X POST -d "apikey=YOUR_API_KEY&resourceid=10113263&attributeid=708&thresholdid=1&requesttype=1&overrideConf=true" \
"https://192.168.129.132:8443/AppManager/xml/configurealarms"

# 配置多个属性
curl -X POST -d "apikey=YOUR_API_KEY&resourceid=10000111&thresholdid=3&attributeid=400,401,53007&requesttype=1&criticalactionid=10000003&overrideConf=true&availabilityCriticalPollCount=4&availabilityClearPollCount=7" \
"https://apm-prod-server:8443/AppManager/xml/configurealarms"

# 监控类型模板
curl -X POST -d "apikey=YOUR_API_KEY&resourceType=PHP&thresholdid=3&attributeid=2304&requesttype=1&overrideConf=false" \
"https://apm-prod-server:8443/AppManager/xml/configurealarms"
```

#### 3.9 响应示例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AppManager-response uri="/AppManager/xml/configurealarms">
  <result>
    <response response-code="4000">
      <message>已成功创建动作</message>
    </response>
  </result>
</AppManager-response>
```

#### 3.10 常见属性 ID

| 监控指标 | 属性 ID | 说明 |
|---------|---------|------|
| 可用性 | 700 | 服务器可用性（宕机检测） |
| 健康状态 | 701 | 整体健康状态 |
| CPU 利用率 | 708 | Linux/Windows CPU 使用率 |
| 内存利用率 | 685 或 702 | 总内存使用率 |
| 磁盘利用率 | 711 或 761 | 磁盘使用率百分比 |

#### 3.11 最佳实践

1. **优先使用阈值模板**：使用 `thresholdid` 关联现有模板，简单可靠
2. **多属性配置**：使用逗号分隔的 `attributeid` 批量配置（如 `708,685,711`）
3. **动作关联**：配置 `criticalactionid` 实现告警通知（微信、邮件等）
4. **轮询计数**：合理设置 `availabilityCriticalPollCount` 避免误报
5. **监控类型模板**：使用 `resourceType` 批量配置同类监控
6. **自定义阈值**：复杂场景建议通过 Web 界面配置，API 有一定限制

#### 3.12 相关脚本

- `configure_alarms_advanced.py` - 高级告警配置示例脚本（10 个示例）
- `setup_alarms.py` - 快速设置可用性和健康状态告警
- `set_cpu_alarm.py` - 专用 CPU 告警配置向导

---

## 维护与状态 API

### 1. 管理/取消管理监控 (Manage/UnManage)

更改监控资源的纳管状态。取消管理后将停止轮询。

**端点**: `Manage` / `UnManage`
**方法**: `POST`

**参数**:
- `resourceid` (必需): 资源 ID

**Python 示例**:
```python
# 取消管理（停止监控）
client.manage_monitor("10113198", action="unmanage")

# 重新管理
client.manage_monitor("10113198", action="manage")
```

---

### 2. 创建维护任务 (CreateMaintenanceTask)

创建计划内停机维护任务。

**端点**: `CreateMaintenanceTask`
**方法**: `POST`

**参数**:
- `taskName`: 任务名称（唯一）
- `resourceid`: 资源 ID 或组 ID
- `taskStartTime`: 开始时间 (HH:mm)
- `taskEndTime`: 结束时间 (HH:mm)
- `taskMethod`: 重复方式 (`once`, `daily`, `weekly`, `monthly`)
- `taskType`: 类型 (`monitor` 或 `group`)
- `taskStatus`: 状态 (`enable` 或 `disable`)
- `taskEffectFrom`: 生效日期 (YYYY-MM-DD)

**Python 示例**:
```python
client.create_maintenance_task(
    name="Nightly Backup",
    resource_id="10113198",
    start_time="02:00",
    end_time="04:00",
    method="daily"
)
```

---

### 3. 获取停机详情 (GetDowntimeSchedulerTask)

查询指定资源的计划停机时间表。

**端点**: `GetDowntimeSchedulerTask`
**方法**: `GET`

**参数**:
- `resourceid`: 资源 ID
- `period`: 周期 (`0`=24h, `1`=7天, `2`=30天)

**Python 示例**:
```python
details = client.get_downtime_details("10113198", period="1")
```

---

## 错误处理

### 响应代码

- `4000`: 成功
- `4001`: 参数错误
- `4002`: 认证失败
- `4003`: 资源不存在
- `4004`: 操作失败

### Python 错误处理示例

```python
result = client.delete_monitor("10113198")

if result and result.get('response-code') == '4000':
    print("操作成功")
else:
    print("操作失败")
    if result:
        print(f"错误信息: {result}")
```

---

## 最佳实践

### 1. 使用 Python 客户端库

推荐使用封装好的 `AppManagerClient` 类，而不是直接调用 REST API：

```python
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# 创建客户端
client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

# 使用高级方法
client.add_linux_monitor(
    ip="192.168.1.100",
    user="root",
    password="password",
    group_id="10113133"
)
```

### 2. 批量操作

使用脚本进行批量添加：

```python
# 使用 batch_add_linux.py
# 1. 编辑 servers.csv
# 2. 运行脚本
python scripts/batch_add_linux.py
```

### 3. 错误重试

对于网络不稳定的环境，建议实现重试机制：

```python
import time

def safe_api_call(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)  # 指数退避
```

### 4. 性能优化

- 使用 `pollInterval=5` (5分钟) 作为默认轮询间隔
- 避免频繁调用 `list_monitors()`，考虑缓存结果
- 批量操作时，添加适当的延迟（如 `time.sleep(1)`）

### 5. 安全建议

- 不要在代码中硬编码 API Key
- 使用环境变量或配置文件存储敏感信息
- 启用 HTTPS 并验证 SSL 证书（生产环境）

---

## 常用脚本

### 查找并删除监控

```bash
# 方法1：通过 IP 地址
python scripts/delete_monitor.py 192.168.130.45

# 方法2：直接通过资源 ID
python scripts/delete_monitor.py 10113198 --id
```

### 健康巡检

```bash
python scripts/health_report.py
```

### 实时监控看板

```bash
python scripts/linux_dashboard.py <resource_id>
```

---

## 参考资料

- [官方 REST API 文档](https://www.manageengine.com/products/applications_manager/help/v1-rest-apis.html)
- [ManageEngine Applications Manager 主页](https://www.manageengine.com/products/applications_manager/)

---

**文档版本**: 1.0
**最后更新**: 2026-02-09
**维护者**: manage-engine skill
