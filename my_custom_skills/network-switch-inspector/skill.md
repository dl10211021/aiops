---
name: network-switch-inspector
description: 通过SSH对H3C和华为网络交换机进行全面巡检。收集系统信息、接口状态、CPU/内存使用率、环境数据和日志。为每台设备生成AI分析的HTML报告，包含健康评分、问题检测和优化建议。支持批量处理和汇总索引报告。针对大规模部署（100+设备）进行优化。
---

# 📡 网络交换机巡检工具 v2.2

> 专业级网络交换机自动化巡检与AI智能分析系统

全面的网络交换机巡检工具，支持H3C和华为交换机。通过SSH连接自动收集设备信息、性能指标、接口状态和环境数据，生成具有搜索、筛选和智能分析功能的交互式AI驱动HTML报告。针对大规模部署优化。

---

## 📋 目录

- [核心特性](#核心特性)
- [快速上手](#快速上手)
- [巡检模式](#巡检模式)
- [报告生成](#报告生成)
- [使用场景](#使用场景)
- [命令参考](#命令参考)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## ✨ 核心特性

### 🚀 主要功能
- **直接IP模式**：无需配置文件，直接指定IP地址即可巡检
- **6种巡检模式**：quick、standard、full、health、network、security
- **54+巡检项目**：全面覆盖系统、网络、性能、安全、环境等各个方面
- **AI智能分析**：自动健康评分（0-100分）、问题检测、优化建议
- **批量处理**：支持多设备并行配置，顺序执行确保稳定性
- **专业报告**：独立设备报告 + 汇总索引，交互式HTML界面

### 🎯 核心价值
- ⚡ **快速评估**：3分钟内完成多台设备健康检查
- 🔍 **提前预警**：智能阈值监控，故障发生前识别潜在问题
- 📊 **数据驱动**：标准化数据收集，支持趋势分析和容量规划
- 🤖 **AI赋能**：自动问题分类、优先级排序、可操作建议
- 📁 **历史追溯**：JSON原始数据 + HTML报告，完整记录设备状态

### 🏢 适用场景
- **日常运维**：每日健康检查、每周例行巡检、每月详细审计
- **故障排查**：快速收集设备信息、定位性能瓶颈、分析配置问题
- **变更管理**：变更前后对比、配置审计、合规性检查
- **容量规划**：资源使用率监控、趋势分析、扩容决策支持
- **应急响应**：快速全面诊断、问题优先级排序、恢复建议

---

## 🚀 快速上手

### 一键巡检（推荐方式）

#### 1️⃣ 单台设备快速巡检

```bash
cd scripts
python switch_inspector.py 192.168.1.1 -u admin -p password -v h3c -m quick
python ai_batch_report_generator.py inspection_results_*.json
```

**适用场景**：日常快速健康检查（30秒完成）

#### 2️⃣ 多台设备批量巡检

```bash
cd scripts
python switch_inspector.py 192.168.1.1 192.168.1.2 192.168.1.3 -u admin -p password -v h3c -m standard
python ai_batch_report_generator.py inspection_results_*.json
```

**适用场景**：例行巡检、周期性检查（每台约2分钟）

#### 3️⃣ 全面详细巡检

```bash
cd scripts
python switch_inspector.py 192.168.46.2 192.168.46.3 192.168.46.4 -u admin -p chervon999 -v h3c -m full
python ai_batch_report_generator.py inspection_results_*.json
```

**适用场景**：详细审计、故障排查、年度检查（每台约5-10分钟）

**输出结果**：
```
ai_reports/
├── AI_Report_192_168_1_1_20260204_120000.html    # 独立设备报告（32KB，800+行）
├── AI_Report_192_168_1_2_20260204_120000.html
├── AI_Report_192_168_1_3_20260204_120000.html
└── Index_Report_20260204_120000.html             # 汇总索引报告（6.5KB）
```

### 命令参数说明

| 参数 | 说明 | 必需 | 默认值 | 示例 |
|------|------|------|--------|------|
| `IP地址` | 一个或多个IP地址 | ✅ | - | `192.168.1.1 192.168.1.2` |
| `-u, --username` | SSH用户名 | ✅ | - | `admin` |
| `-p, --password` | SSH密码 | ✅ | - | `password123` |
| `-v, --vendor` | 厂商类型 | ✅ | - | `h3c` 或 `huawei` |
| `-m, --mode` | 巡检模式 | ❌ | `standard` | `quick/full/health/network/security` |
| `-P, --port` | SSH端口 | ❌ | `22` | `2222` |
| `-t, --timeout` | 连接超时（秒） | ❌ | `15` | `30` |
| `-i, --items` | 指定巡检项目 | ❌ | 全部 | `system_info cpu_memory interfaces` |

---

## 🎯 巡检模式

提供6种预定义巡检模式，满足不同场景需求：

### 模式对比表

| 模式 | 项目数 | 耗时 | 适用场景 | 建议频率 | 命令 |
|------|--------|------|----------|----------|------|
| 🟢 **quick** | 8项 | 30秒 | 快速健康检查 | 每天 | `-m quick` |
| 🔵 **standard** | 17项 | 2分钟 | 例行巡检 | 每周 | 默认 |
| 🟣 **full** | 54+项 | 5-10分钟 | 全面审计 | 每月 | `-m full` |
| 🟡 **health** | 13项 | 1分钟 | 性能监控 | 每天 | `-m health` |
| 🟠 **network** | 13项 | 2分钟 | 网络检查 | 每周 | `-m network` |
| 🔴 **security** | 8项 | 1分钟 | 安全审计 | 每周 | `-m security` |

### 各模式详细说明

#### 🟢 quick - 快速巡检
**检查项目（8项）**：系统信息、CPU、内存、接口、温度、电源、风扇、日志
**使用场景**：
- ✅ 每日晨检，快速确认设备在线
- ✅ 变更后即时验证
- ✅ 告警触发后快速诊断

```bash
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m quick
```

#### 🔵 standard - 标准巡检（默认）
**检查项目（17项）**：基础信息 + 网络基础 + 环境 + STP + LLDP
**使用场景**：
- ✅ 每周例行巡检
- ✅ 月度报告数据收集
- ✅ 部门内部设备检查

```bash
python switch_inspector.py 192.168.1.1 192.168.1.2 -u admin -p pass -v h3c
```

#### 🟣 full - 全面巡检
**检查项目（54+项）**：所有可用检查项目
**使用场景**：
- ✅ 年度审计和合规检查
- ✅ 重大变更前后对比
- ✅ 复杂故障深度排查
- ✅ 设备移交验收

```bash
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m full
```

#### 🟡 health - 健康检查
**检查项目（13项）**：系统信息、CPU、内存、CPU历史、进程、接口统计、接口错误、环境、告警
**使用场景**：
- ✅ 性能监控和容量规划
- ✅ 资源使用率分析
- ✅ 硬件健康状态评估

```bash
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m health
```

#### 🟠 network - 网络巡检
**检查项目（13项）**：接口、VLAN、MAC、ARP、路由、STP、链路聚合、LLDP、OSPF、BGP
**使用场景**：
- ✅ 网络拓扑变更验证
- ✅ 路由协议状态检查
- ✅ 二三层网络问题排查

```bash
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m network
```

#### 🔴 security - 安全审计
**检查项目（8项）**：用户、SSH、802.1X、端口安全、ACL、日志、告警
**使用场景**：
- ✅ 安全合规检查
- ✅ 访问权限审计
- ✅ 安全策略验证

```bash
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m security
```

---

## 📊 报告生成

### AI批量报告生成器（v2.2新功能）

#### 生成报告

```bash
python ai_batch_report_generator.py inspection_results_YYYYMMDD_HHMMSS.json
```

**自动创建**：
1. **独立设备报告**（每台设备一个HTML文件）
   - 健康评分：0-100分，4级分类（优秀≥90、良好≥75、警告≥60、严重<60）
   - AI综合分析：系统优势、性能分析、风险识别
   - 问题清单：按严重程度分类，提供具体影响和建议
   - 9大章节：设备信息、AI分析、问题风险、接口状态、网络配置、优化建议、性能趋势、风险评估、巡检结论

2. **汇总索引报告**（一个HTML文件）
   - 设备统计：总数、平均健康分、状态分布
   - 设备列表：名称、IP、健康分、状态、问题数
   - 快速导航：点击设备名称跳转到独立报告

#### 报告特性

**🎨 视觉设计**
- ✅ 专业渐变配色，清晰的视觉层次
- ✅ 响应式布局，支持桌面/平板/手机
- ✅ 状态色彩编码：绿色（正常）、黄色（警告）、红色（严重）

**🔍 交互功能**
- ✅ 实时搜索：按设备名称或IP筛选
- ✅ 状态过滤：一键查看正常/警告/严重设备
- ✅ 可折叠列表：大规模部署（100+设备）性能优化
- ✅ 选项卡导航：系统信息、性能指标、接口状态、环境监控、系统日志

**🤖 AI智能分析**

| 监控项 | 正常 | 警告 | 严重 |
|--------|------|------|------|
| CPU使用率 | <50% | 50-80% | >80% |
| 内存使用率 | <70% | 70-85% | >85% |
| 温度 | <50°C | 50-65°C | >65°C |
| 接口状态 | 全部UP | 少量DOWN | 大量DOWN |
| 光功率 | -10~0 dBm | -15~-10 dBm | <-15 dBm |

**📁 报告结构**

```
ai_reports/
├── AI_Report_192_168_46_2_20260204_105651.html    # 设备1详细报告（32KB）
│   ├── 📋 设备基本信息（8项）
│   ├── 🤖 AI综合健康分析
│   ├── ⚠️ 发现的问题与风险
│   ├── 🔌 接口状态分析
│   ├── 🌐 网络配置分析
│   ├── 💡 专业优化建议
│   ├── 📊 性能趋势与预测
│   ├── 🛡️ 风险评估与应急预案
│   └── ✅ 巡检结论
├── AI_Report_192_168_46_3_20260204_105651.html    # 设备2详细报告
├── AI_Report_192_168_46_4_20260204_105651.html    # 设备3详细报告
└── Index_Report_20260204_105651.html              # 汇总索引报告（6.5KB）
    ├── 📊 整体统计仪表板
    ├── 🔍 搜索和筛选功能
    └── 📑 设备列表（含快速跳转链接）
```

---

## 💼 使用场景

### 场景1：每日健康检查

**需求**：快速确认关键设备运行正常

```bash
# 1. 快速巡检（30秒/台）
cd scripts
python switch_inspector.py 192.168.1.1 192.168.1.2 192.168.1.3 -u admin -p pass -v h3c -m quick

# 2. 生成报告
python ai_batch_report_generator.py inspection_results_*.json

# 3. 查看汇总报告
# 打开 ai_reports/Index_Report_*.html
# 如果全部显示"优秀"或"良好"，则设备正常
# 如果有"警告"或"严重"，点击查看详细报告
```

**关注重点**：
- ✅ CPU和内存使用率是否正常
- ✅ 是否有DOWN的关键接口
- ✅ 温度、电源、风扇是否正常
- ✅ 是否有新的告警日志

---

### 场景2：每周例行巡检

**需求**：全面检查网络设备状态，生成周报

```bash
# 1. 标准巡检（2分钟/台）
cd scripts
python switch_inspector.py 192.168.1.1 192.168.1.2 192.168.1.3 192.168.1.4 \
    -u admin -p pass -v h3c -m standard

# 2. 生成报告
python ai_batch_report_generator.py inspection_results_*.json

# 3. 归档报告
mkdir -p ../weekly_reports/2026-W06
cp ai_reports/*.html ../weekly_reports/2026-W06/
```

**关注重点**：
- ✅ 资源使用趋势（与上周对比）
- ✅ 接口流量和错误统计
- ✅ STP拓扑变化
- ✅ MAC/ARP表异常
- ✅ 优化建议的落实情况

---

### 场景3：故障排查

**需求**：设备出现性能问题，需要快速诊断

```bash
# 1. 全面巡检单台设备（5-10分钟）
cd scripts
python switch_inspector.py 192.168.1.10 -u admin -p pass -v h3c -m full

# 2. 生成详细报告
python ai_batch_report_generator.py inspection_results_*.json

# 3. 分析报告
# 打开 ai_reports/AI_Report_192_168_1_10_*.html
# 重点查看：
# - AI综合健康分析：识别主要问题
# - 发现的问题与风险：按优先级排序
# - 性能趋势与预测：查看CPU/内存/温度趋势
# - 专业优化建议：获取具体解决方案
```

**排查步骤**：
1. 查看健康评分和整体状态
2. 检查"发现的问题与风险"章节
3. 分析性能指标（CPU、内存、温度）
4. 检查接口状态和错误统计
5. 查看系统日志中的异常信息
6. 根据AI建议采取行动

---

### 场景4：变更管理

**需求**：网络设备配置变更前后对比

```bash
# 变更前：全面巡检并保存基准
cd scripts
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m full
python ai_batch_report_generator.py inspection_results_*.json
cp -r ai_reports ../change_baseline/before_change_20260204

# 执行变更...

# 变更后：再次全面巡检
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m full
python ai_batch_report_generator.py inspection_results_*.json
cp -r ai_reports ../change_baseline/after_change_20260204

# 对比两次报告，重点关注：
# - 健康评分变化
# - 新增的问题或告警
# - 接口状态变化
# - 路由/VLAN/MAC表变化
```

---

### 场景5：合规审计

**需求**：安全合规检查，生成审计报告

```bash
# 1. 安全审计模式巡检
cd scripts
python switch_inspector.py 192.168.1.1 192.168.1.2 192.168.1.3 \
    -u admin -p pass -v h3c -m security

# 2. 生成报告
python ai_batch_report_generator.py inspection_results_*.json

# 3. 自定义审计报告（可选）
python switch_inspector.py 192.168.1.1 192.168.1.2 -u admin -p pass -v h3c \
    -i system_info users ssh_status acl port_security dot1x logs
```

**审计重点**：
- ✅ 用户账户管理（弱密码、过期账户）
- ✅ SSH配置（密钥认证、版本、加密算法）
- ✅ ACL规则有效性
- ✅ 端口安全配置
- ✅ 802.1X认证状态
- ✅ 日志记录和审计跟踪

---

## 📚 命令参考

### 巡检命令速查表

```bash
# ============ 基础命令 ============

# 单台设备（最简）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c

# 多台设备（批量）
python switch_inspector.py 192.168.1.1 192.168.1.2 192.168.1.3 -u admin -p pass -v h3c

# ============ 模式选择 ============

# 快速模式（30秒）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m quick

# 标准模式（2分钟，默认）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m standard

# 全面模式（5-10分钟）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m full

# 健康检查（1分钟）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m health

# 网络检查（2分钟）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m network

# 安全审计（1分钟）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m security

# ============ 自定义项目 ============

# 只检查CPU和内存
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c \
    -i cpu_memory memory_usage

# 只检查接口和日志
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c \
    -i interfaces interface_status logs

# ============ 报告生成 ============

# 生成AI报告（推荐）
python ai_batch_report_generator.py inspection_results_*.json

# 生成报告（指定文件）
python ai_batch_report_generator.py inspection_results_20260204_120000.json

# ============ 高级参数 ============

# 自定义SSH端口
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -P 2222

# 增加超时时间（慢速网络）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -t 30

# 华为交换机
python switch_inspector.py 192.168.1.1 -u admin -p pass -v huawei -m full
```

### 可用巡检项目列表

#### 基础系统信息（6项）
- `system_info` - 系统版本信息
- `device_info` - 设备硬件信息
- `cpu_memory` - CPU使用率
- `memory_usage` - 内存使用情况
- `bootrom_info` - BootROM信息
- `flash_info` - Flash存储信息

#### 接口和链路（7项）
- `interfaces` - 接口简要状态
- `interface_status` - 接口详细状态
- `interface_counters` - 接口流量统计
- `interface_errors` - 接口错误统计
- `link_flap` - 链路闪断记录
- `transceiver` / `optical_module` - 光模块诊断
- `transceiver_info` / `optical_diagnosis` - 光模块详细信息

#### 二层网络（8项）
- `vlan` - VLAN配置
- `vlan_all` - VLAN详细信息
- `mac_table` - MAC地址表
- `mac_statistics` - MAC地址统计
- `stp` - STP完整信息
- `stp_brief` - STP简要状态
- `lacp` / `eth_trunk` - 链路聚合状态
- `lldp_neighbor` - LLDP邻居发现

#### 三层网络（6项）
- `arp_table` - ARP表
- `arp_statistics` - ARP统计
- `routing_table` - 路由表
- `routing_statistics` - 路由统计
- `ospf_peer` - OSPF邻居
- `bgp_peer` - BGP邻居

#### 性能和资源（4项）
- `qos_policy` - QoS策略
- `acl` - 访问控制列表
- `cpu_history` - CPU历史记录
- `process` - 进程CPU占用

#### 安全和认证（5项）
- `users` - 当前登录用户
- `ssh_status` - SSH服务状态
- `ssh_session` - SSH会话信息
- `dot1x` - 802.1X认证
- `port_security` - 端口安全

#### 环境监控（4项）
- `temperature` - 温度状态
- `power` - 电源状态
- `fan` - 风扇状态
- `alarm` - 告警信息

#### 日志和诊断（5项）
- `logs` - 系统日志
- `logs_reverse` - 反向日志（最新在前）
- `diagnostic` - 诊断信息
- `ntp` - NTP时间同步状态
- `clock` - 系统时钟

#### 配置和备份（4项）
- `current_config` - 当前运行配置
- `saved_config` - 已保存配置
- `config_diff` - 配置变更记录
- `startup_info` - 启动配置信息

#### 堆叠和虚拟化（3-4项）
- `irf` / `stack` - 堆叠状态
- `irf_link` / `stack_port` - 堆叠链路/端口
- `mad` / `css` - MAD检测/CSS集群

---

## 🎓 最佳实践

### 安全性

#### 1. 凭据管理
```bash
# ❌ 不推荐：密码直接写在命令行
python switch_inspector.py 192.168.1.1 -u admin -p MyPassword123

# ✅ 推荐：使用环境变量
export SWITCH_USER="admin"
export SWITCH_PASS="MyPassword123"
python switch_inspector.py 192.168.1.1 -u $SWITCH_USER -p $SWITCH_PASS -v h3c

# ✅ 推荐：使用只读账户
python switch_inspector.py 192.168.1.1 -u readonly -p pass -v h3c

# ✅ 推荐：限制配置文件权限（使用YAML时）
chmod 600 devices.yaml
```

#### 2. 网络访问
- ✅ 从管理网络运行巡检
- ✅ 使用跳板机访问生产环境
- ✅ 配置ACL限制SSH访问源IP
- ✅ 定期审计巡检账户使用情况

---

### 执行策略

#### 1. 巡检计划

| 频率 | 模式 | 执行时间 | 目标 |
|------|------|----------|------|
| 每天 | quick | 早上8:00 | 快速健康检查 |
| 每周一 | standard | 晚上21:00 | 例行巡检 |
| 每月1号 | full | 凌晨2:00 | 详细审计 |
| 按需 | health/network/security | 工作时间 | 针对性检查 |

#### 2. 性能优化
```bash
# ❌ 不推荐：并行巡检（可能导致网络拥塞）
# 工具已自动顺序执行

# ✅ 推荐：分批执行（大量设备）
# 批次1：核心交换机（凌晨）
python switch_inspector.py 192.168.1.1 192.168.1.2 -u admin -p pass -v h3c -m full

# 批次2：汇聚交换机（凌晨1点）
python switch_inspector.py 192.168.2.1 192.168.2.2 -u admin -p pass -v h3c -m full

# 批次3：接入交换机（凌晨2点）
python switch_inspector.py 192.168.3.1 192.168.3.2 -u admin -p pass -v h3c -m standard
```

#### 3. 慢速网络处理
```bash
# 增加超时时间
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -t 30

# 使用快速模式减少数据收集
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m quick
```

---

### 报告管理

#### 1. 目录结构（推荐）

```
switch_inspection/
├── scripts/                          # 巡检脚本
│   ├── switch_inspector.py
│   ├── ai_batch_report_generator.py
│   └── ai_reports/                   # 最新报告
├── daily_reports/                    # 每日报告归档
│   ├── 2026-02-01/
│   ├── 2026-02-02/
│   └── 2026-02-03/
├── weekly_reports/                   # 每周报告归档
│   ├── 2026-W05/
│   └── 2026-W06/
├── monthly_reports/                  # 每月报告归档
│   ├── 2026-01/
│   └── 2026-02/
└── raw_data/                         # JSON原始数据
    ├── inspection_results_20260201_*.json
    └── inspection_results_20260202_*.json
```

#### 2. 自动归档脚本

```bash
#!/bin/bash
# auto_archive.sh - 自动归档巡检报告

DATE=$(date +%Y-%m-%d)
REPORT_DIR="daily_reports/$DATE"

# 创建目录
mkdir -p $REPORT_DIR

# 执行巡检
cd scripts
python switch_inspector.py 192.168.1.1 192.168.1.2 -u admin -p pass -v h3c -m standard
python ai_batch_report_generator.py inspection_results_*.json

# 归档报告
cp ai_reports/*.html ../$REPORT_DIR/
cp inspection_results_*.json ../raw_data/

# 清理30天前的报告
find ../daily_reports -type d -mtime +30 -exec rm -rf {} \;

echo "✅ 报告已归档到 $REPORT_DIR"
```

#### 3. 报告审查清单

**日常审查（每日快速检查）**
- [ ] 所有设备健康评分 ≥75分
- [ ] 无"严重"状态设备
- [ ] CPU使用率 <80%
- [ ] 内存使用率 <85%
- [ ] 无关键接口DOWN
- [ ] 温度 <65°C
- [ ] 无新增告警

**周度审查（每周详细检查）**
- [ ] 资源使用率趋势正常
- [ ] 接口错误率 <0.01%
- [ ] MAC/ARP表无异常
- [ ] STP拓扑稳定
- [ ] 路由协议邻居正常
- [ ] 日志无异常模式
- [ ] 优化建议已记录

**月度审查（每月全面检查）**
- [ ] 配置备份已完成
- [ ] 配置变更已审计
- [ ] 安全策略已验证
- [ ] 容量规划数据已收集
- [ ] 趋势分析已完成
- [ ] 维护计划已更新

---

## 🔧 故障排查

### 常见问题及解决方案

#### ❌ 问题1：SSH连接失败

**症状**：
```
Error: Failed to connect to 192.168.1.1: Connection timeout
```

**排查步骤**：
```bash
# 1. 检查网络连通性
ping 192.168.1.1

# 2. 检查SSH端口
telnet 192.168.1.1 22

# 3. 尝试手动SSH登录
ssh admin@192.168.1.1

# 4. 检查防火墙规则
# 确保源IP可以访问目标设备的SSH端口

# 5. 增加超时时间重试
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -t 30
```

**可能原因**：
- ✅ 网络不通（路由问题、防火墙）
- ✅ SSH服务未启用
- ✅ 错误的SSH端口
- ✅ 连接超时时间过短
- ✅ 设备负载过高响应慢

---

#### ❌ 问题2：认证失败

**症状**：
```
Error: Authentication failed for 192.168.1.1
```

**排查步骤**：
```bash
# 1. 验证用户名和密码
ssh admin@192.168.1.1
# 手动输入密码确认

# 2. 检查账户是否被锁定
# 登录设备查看：display local-user

# 3. 检查密码特殊字符
# 如果密码包含特殊字符，尝试用单引号包裹：
python switch_inspector.py 192.168.1.1 -u admin -p 'Pass@123!' -v h3c

# 4. 检查用户权限级别
# 确保账户至少有级别1（display命令）权限
```

**可能原因**：
- ✅ 用户名或密码错误
- ✅ 账户被锁定或过期
- ✅ 密码包含特殊字符未正确转义
- ✅ 账户权限不足

---

#### ❌ 问题3：部分命令执行失败

**症状**：
```
Warning: Command 'display cpu-usage' failed on 192.168.1.1
```

**排查步骤**：
```bash
# 1. 手动登录设备测试命令
ssh admin@192.168.1.1
display cpu-usage

# 2. 检查设备型号和软件版本
# 某些老旧设备可能不支持特定命令

# 3. 使用较少项目的模式
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m quick

# 4. 检查用户权限
# 确保账户有执行该命令的权限
```

**可能原因**：
- ✅ 设备型号不支持该命令
- ✅ 软件版本过旧
- ✅ 用户权限不足
- ✅ 命令语法不兼容

---

#### ❌ 问题4：报告生成失败

**症状**：
```
Error: Failed to generate report from inspection_results_20260204.json
```

**排查步骤**：
```bash
# 1. 检查JSON文件是否存在且完整
ls -lh inspection_results_*.json
cat inspection_results_*.json | python -m json.tool > /dev/null

# 2. 检查磁盘空间
df -h

# 3. 检查文件权限
chmod 644 inspection_results_*.json

# 4. 手动指定JSON文件
python ai_batch_report_generator.py inspection_results_20260204_120000.json

# 5. 查看详细错误信息
python ai_batch_report_generator.py inspection_results_*.json 2>&1 | more
```

**可能原因**：
- ✅ JSON文件不存在或损坏
- ✅ 磁盘空间不足
- ✅ 文件权限问题
- ✅ JSON格式错误（特殊字符）

---

#### ❌ 问题5：巡检速度过慢

**症状**：
单台设备巡检超过10分钟

**优化方案**：
```bash
# 1. 使用更快的模式
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -m quick

# 2. 只巡检必要项目
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c \
    -i system_info cpu_memory interfaces temperature

# 3. 增加超时时间（避免等待）
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c -t 30

# 4. 检查设备负载
# 登录设备执行：display cpu-usage
# 如果CPU过高，考虑在业务低峰期执行

# 5. 检查网络延迟
ping -c 10 192.168.1.1
# 如果延迟过高，检查网络路径
```

---

### 调试模式

如果遇到未知问题，可以查看详细日志：

```bash
# 方法1：查看Python脚本输出
python switch_inspector.py 192.168.1.1 -u admin -p pass -v h3c 2>&1 | tee debug.log

# 方法2：检查生成的JSON文件
cat inspection_results_*.json | python -m json.tool | less

# 方法3：手动测试SSH连接
ssh -vvv admin@192.168.1.1
```

---

## 📦 依赖项和要求

### Python环境

**要求**：
- Python 3.6 或更高版本
- pip 包管理器

**安装依赖**：
```bash
cd D:\cherry\.claude\skills\network-switch-inspector
pip install -r requirements.txt
```

**依赖库**：
- `paramiko` - SSH客户端库
- `pyyaml` - YAML配置文件解析

---

### 网络要求

- ✅ SSH访问：所有目标交换机的SSH端口（通常22）
- ✅ 网络连接：从运行脚本的机器到所有交换机
- ✅ 有效凭据：具有足够权限执行display命令的账户

---

### 交换机要求

#### H3C交换机
- **系统版本**：Comware 5.x 或更高版本
- **SSH服务**：已启用
- **用户权限**：至少级别1（display命令）权限
- **测试型号**：S5500、S5800、S6800、S12500系列
- **特殊功能**：支持IRF（Intelligent Resilient Framework）

#### 华为交换机
- **系统版本**：VRP 5.x 或更高版本
- **SSH服务**：已启用（STelnet）
- **用户权限**：至少级别1（display命令）权限
- **测试型号**：S5700、S6700、CE6800、CE12800系列
- **特殊功能**：支持CSS（Cluster Switch System）、iStack、CloudEngine

---

## 📝 版本历史

### v2.2（当前版本）- 2026-02-04
**新增功能**：
- ✅ AI批量报告生成器：独立设备报告 + 汇总索引
- ✅ 健康评分算法：0-100分评分系统
- ✅ 9章节详细报告：包含性能趋势与风险评估
- ✅ 专业渐变设计：移动响应式布局

**改进**：
- ✅ 报告大小：从344行扩展到800+行（32KB）
- ✅ 分析深度：系统优势、风险矩阵、应急预案
- ✅ 用户体验：直接链接、快速导航、状态筛选

### v2.1 - 2026-02-03
**新增功能**：
- ✅ 交互式报告：搜索、筛选、可折叠视图
- ✅ 大规模支持：优化100+设备部署
- ✅ 响应式设计：桌面/平板/手机适配

### v2.0 - 初始版本
**核心功能**：
- ✅ 直接IP模式
- ✅ 6种巡检模式
- ✅ 54+巡检项目
- ✅ AI智能分析
- ✅ HTML报告生成

---

## 🔗 相关资源

### 技能文件
- `skill.md` - 本文档（使用指南）
- `scripts/switch_inspector.py` - 主巡检脚本
- `scripts/ai_batch_report_generator.py` - AI报告生成器
- `requirements.txt` - Python依赖列表

### 参考文档
- `references/h3c_commands.md` - H3C命令参考
- `references/huawei_commands.md` - 华为命令参考
- `references/inspection_checklist.md` - 巡检标准清单

### 配置示例
- `assets/devices_example.yaml` - YAML配置模板

---

## 💡 常见问题 FAQ

### Q1：支持哪些厂商的交换机？
**A**：目前支持H3C（Comware 5.x+）和华为（VRP 5.x+）交换机。未来计划支持Cisco、Juniper等厂商。

### Q2：是否会修改交换机配置？
**A**：不会。本工具仅执行只读的show/display命令，不会对设备配置进行任何修改。

### Q3：可以同时巡检多少台设备？
**A**：理论上无限制，但建议单次巡检设备数量根据网络环境和时间窗口合理安排。工具会顺序执行以确保稳定性。

### Q4：巡检数据保存多久？
**A**：工具不会自动删除数据，建议按需归档并至少保留90天的历史记录用于趋势分析。

### Q5：能否定时自动执行巡检？
**A**：可以。使用系统计划任务（Windows任务计划程序或Linux crontab）配合脚本实现自动化巡检。

### Q6：报告可以导出PDF吗？
**A**：HTML报告可以直接在浏览器中打印为PDF（Ctrl+P → 另存为PDF）。

### Q7：如何处理密码中的特殊字符？
**A**：使用单引号包裹密码，如：`-p 'Pass@123!'`

### Q8：支持SSH密钥认证吗？
**A**：当前版本仅支持密码认证，SSH密钥认证在计划中。

---

## 📧 技术支持

遇到问题时，请按以下步骤操作：

1. **自助排查**：查看本文档的"故障排查"章节
2. **检查环境**：验证Python版本、依赖库、网络连接
3. **测试连接**：手动SSH登录设备确认凭据和权限
4. **收集信息**：
   - 交换机型号和软件版本
   - 错误消息或异常行为
   - 命令输出样本（脱敏后）
   - 执行的完整命令

---

## 📄 许可和免责声明

本工具仅用于合法的网络设备运维和管理。使用者应确保：
- ✅ 获得设备所有者的授权
- ✅ 遵守组织的安全策略
- ✅ 妥善保管设备凭据
- ✅ 定期审计巡检活动

---

**🎉 享受自动化巡检带来的高效运维体验！**
