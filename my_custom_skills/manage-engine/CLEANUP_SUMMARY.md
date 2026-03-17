# ManageEngine Skill 整理说明

## 已完成的更新

### 1. 脚本更新
- **query_thresholds.py**: 去掉了 Web 查看提示，改为 API 说明
- **setup_alarms.py**: 去掉了 Web 界面访问建议，改为使用其他脚本查看

### 2. 核心功能说明

#### 查询告警配置
```bash
# 查看系统所有告警动作和当前告警
python scripts/query_thresholds.py

# 查看特定监控器配置
python scripts/query_thresholds.py 10113263
```

**输出内容:**
- 告警动作列表（30个微信机器人）
- 当前活动告警（777个）
- 监控器详细配置
- 监控器当前值

#### 配置告警
```bash
# 方式1: 快速配置基础告警（可用性+健康状态）
python scripts/setup_alarms.py 10113263 10000012

# 方式2: 高级配置（10种场景）
python scripts/configure_alarms_advanced.py 10 10113263 10000012

# 方式3: 单独配置CPU告警
python scripts/set_cpu_alarm.py 10113263 90 80
```

### 3. API 限制说明

**不可用的 API（返回404）:**
- `ListThresholdProfiles` - 无法获取阈值配置文件列表
- `GetAlarmDetails` - 无法获取告警详情
- `GetThresholdDetails` - 无法获取阈值详情
- `GetConfiguredAlarms` - 无法获取已配置告警

**可用的 API:**
- ✅ `ListAlarms` - 获取当前告警列表
- ✅ `ListActions` - 获取告警动作列表
- ✅ `GetMonitorData` - 获取监控器数据
- ✅ `configurealarms` - 配置告警（POST方式）

### 4. 告警配置最佳实践

**步骤1: 查看可用的告警动作**
```bash
python scripts/query_thresholds.py
```
找到需要的微信机器人ID（如：10000012 - 丁露微信机器人）

**步骤2: 配置告警**
```bash
# 配置基础告警
python scripts/setup_alarms.py <resource_id> <action_id>

# 或配置完整告警（包括CPU、内存、磁盘）
python scripts/configure_alarms_advanced.py 10 <resource_id> <action_id>
```

**步骤3: 验证配置**
```bash
# 查看配置结果
python scripts/query_thresholds.py <resource_id>

# 检查当前告警状态
python scripts/health_report.py
```

### 5. 常用告警动作 ID

| 动作ID | 名称 | 使用次数 |
|--------|------|---------|
| 10000012 | 丁露微信机器人 | 33313 |
| 10000011 | 顾友峰微信机器人 | 36541 |
| 10000007 | 基础架构微信机器人 | 4283 |
| 10000008 | 刘洋舟微信机器人 | 4541 |
| 10000005 | 费新建团队微信机器人 | 4423 |

### 6. 常用属性 ID

| 属性ID | 属性名称 | 说明 |
|--------|---------|------|
| 700 | Availability | 可用性（服务器宕机） |
| 701 | Health Status | 健康状态 |
| 708 | CPU Utilization | CPU 利用率 |
| 685 | Memory Utilization | 内存利用率 |
| 711 | Disk Utilization | 磁盘利用率 |

### 7. 配置示例

#### 示例1: 配置服务器基础告警
```bash
# 为新服务器配置可用性和健康状况告警
python scripts/setup_alarms.py 10113263 10000012
```

#### 示例2: 配置完整监控告警
```bash
# 配置可用性、健康、CPU、内存、磁盘告警
python scripts/configure_alarms_advanced.py 10 10113263 10000012
```

#### 示例3: API 方式配置自定义阈值
```python
from scripts.manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

# 配置CPU告警：>90%严重，>80%警告，连续3次确认
client.configure_alarm(
    resource_id='10113263',
    attribute_id='708',
    critical_threshold=90,
    warning_threshold=80,
    critical_action_id='10000012',
    warning_action_id='10000012',
    consecutive_critical_polls=3,
    consecutive_warning_polls=2,
    request_type=1,
    override_conf=True
)
```

## 文件清单

### 核心API库
- `scripts/manage_engine_api.py` - 核心API客户端类

### 查询工具
- `scripts/query_thresholds.py` - 查询告警配置和系统状态
- `scripts/health_report.py` - 全系统健康报告
- `scripts/linux_dashboard.py` - 实时性能看板

### 配置工具
- `scripts/setup_alarms.py` - 快速配置基础告警
- `scripts/configure_alarms_advanced.py` - 高级告警配置（10种场景）
- `scripts/set_cpu_alarm.py` - 快速配置CPU告警
- `scripts/configure_threshold.py` - 查看和配置阈值

### 监控管理
- `scripts/add_linux.py` - 添加单台Linux服务器
- `scripts/add_linux_group.py` - 添加服务器并自动入组
- `scripts/batch_add_linux.py` - 批量添加服务器（CSV）
- `scripts/delete_monitor.py` - 删除监控器

### 文档
- `API_REFERENCE.md` - 完整API参考文档
- `CONFIGURE_ALARMS_README.md` - 告警配置详细说明
- `skill.md` - Skill主文档

## 下一步建议

1. **测试告警配置**: 使用 `setup_alarms.py` 为测试服务器配置告警
2. **批量配置**: 编写脚本批量为所有服务器配置标准告警
3. **监控自动化**: 结合添加监控和告警配置，实现一键纳管
