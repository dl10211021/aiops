# 华为交换机命令参考

本文档提供华为交换机常用巡检命令的详细说明。

## 系统信息

### display version
显示设备版本信息、硬件信息、系统运行时间等。

**输出包含**：
- 设备型号
- 软件版本号（VRP版本）
- 硬件版本号
- CPLD版本
- 设备序列号（ESN）
- 系统运行时间

**示例输出**：
```
Huawei Versatile Routing Platform Software
VRP (R) software, Version 8.180 (CE6857EI V200R019C10SPC800)
Copyright (C) 2012-2020 Huawei Technologies Co., Ltd.
HUAWEI CE6857-48S6CQ-EI uptime is 180 days, 5 hours, 23 minutes
```

## 性能监控

### display cpu-usage
显示CPU使用率信息。

**输出包含**：
- 当前CPU使用率
- 5秒平均CPU使用率
- 1分钟平均CPU使用率
- 5分钟平均CPU使用率

**阈值参考**：
- 正常：< 50%
- 警告：50-80%
- 严重：> 80%

### display memory-usage
显示内存使用情况。

**输出包含**：
- 总内存容量
- 已用内存
- 空闲内存
- 内存使用率

**阈值参考**：
- 正常：< 80%
- 警告：80-90%
- 严重：> 90%

## 接口管理

### display interface brief
显示所有接口的简要信息。

**输出包含**：
- 接口名称
- 物理状态（UP/DOWN/*down）
- 协议状态（UP/DOWN）
- 接口描述
- 速率和双工模式
- IP地址（如果配置）

**状态说明**：
- UP：接口物理和协议都正常
- DOWN：接口物理层故障
- *down：接口被管理员关闭

**示例输出**：
```
Interface            PHY   Protocol InUti OutUti   inErrors  outErrors
GigabitEthernet0/0/1 up    up          0%     0%          0          0
GigabitEthernet0/0/2 down  down        --     --          0          0
```

### display interface [interface-name]
显示指定接口的详细信息。

**输出包含**：
- 接口类型和编号
- 当前状态
- 物理参数（速率、双工、流控等）
- IP地址和子网掩码
- 接口描述
- 流量统计（输入/输出字节、包数）
- 错误统计
- 最后状态变更时间

**关键指标**：
- Input errors：输入错误包
- CRC：CRC错误
- Output errors：输出错误
- Collisions：冲突数
- Late collisions：延迟冲突

## VLAN管理

### display vlan
显示所有VLAN配置信息。

**输出包含**：
- VLAN ID
- VLAN名称（Name）
- VLAN状态（Status）
- 包含的接口列表

**示例输出**：
```
VID  Status  Property      MAC-LRN Statistics Description
1    enable  default       enable  disable    VLAN 0001
10   enable  static        enable  disable    Management
```

### display vlan [vlan-id]
显示指定VLAN的详细信息。

### display port vlan
显示接口的VLAN配置信息。

## MAC地址表

### display mac-address
显示MAC地址表。

**输出包含**：
- MAC地址
- VLAN ID
- 学习类型（dynamic/static/blackhole）
- 接口
- 老化时间

**常用参数**：
- `display mac-address interface [interface-name]` - 显示指定接口
- `display mac-address vlan [vlan-id]` - 显示指定VLAN
- `display mac-address count` - 显示统计信息
- `display mac-address aging-time` - 显示老化时间

## ARP表

### display arp
显示ARP表信息。

**输出包含**：
- IP地址
- MAC地址
- VLAN ID
- 接口
- 老化时间
- 类型（D-动态, S-静态, I-接口）

**常用参数**：
- `display arp interface [interface-name]` - 显示指定接口
- `display arp vlan [vlan-id]` - 显示指定VLAN
- `display arp statistics` - 显示ARP统计

## 路由表

### display ip routing-table
显示IP路由表。

**输出包含**：
- 目标网络
- 掩码长度
- 协议类型（Direct/Static/RIP/OSPF/BGP等）
- 优先级（Pre）
- 开销（Cost）
- 下一跳
- 出接口

**常用参数**：
- `display ip routing-table protocol static` - 只显示静态路由
- `display ip routing-table verbose` - 显示详细信息
- `display ip routing-table statistics` - 显示统计信息

## 日志管理

### display logbuffer
显示系统日志缓冲区内容。

**日志级别**：
- 0 - Emergencies：紧急
- 1 - Alerts：告警
- 2 - Critical：严重
- 3 - Errors：错误
- 4 - Warnings：警告
- 5 - Notifications：通知
- 6 - Informational：信息
- 7 - Debugging：调试

**常用参数**：
- `display logbuffer reverse` - 反向显示（最新在前）
- `display logbuffer level warnings` - 显示警告及以上级别
- `display logbuffer | include Error` - 过滤包含Error的日志

### display alarm all
显示所有告警信息。

### display trapbuffer
显示SNMP trap缓冲区。

## 环境监控

### display temperature
显示设备温度信息。

**输出包含**：
- 各部件温度（主控板、接口板等）
- 当前温度值
- 温度阈值
- 温度状态（Normal/Minor/Major/Fatal）

**温度阈值参考**：
- Normal：正常工作温度
- Minor：轻微告警（接近阈值）
- Major：严重告警（超过阈值）
- Fatal：致命告警（严重超标）

### display power
显示电源模块状态。

**输出包含**：
- 电源模块编号
- 状态（Normal/Abnormal）
- 模式（AC/DC）
- 额定功率
- 当前功率
- 温度

### display fan
显示风扇状态。

**输出包含**：
- 风扇编号
- 状态（Normal/Abnormal）
- 转速（RPM）
- 转速百分比

## 链路聚合

### display eth-trunk
显示Eth-Trunk（链路聚合）信息。

**输出包含**：
- Eth-Trunk ID
- 工作模式（手动/LACP）
- 成员接口
- 活动成员接口
- 负载分担方式

### display eth-trunk [trunk-id]
显示指定Eth-Trunk的详细信息。

## 堆叠信息

### display stack
显示堆叠信息（适用于堆叠交换机）。

**输出包含**：
- 成员ID
- 角色（Master/Standby/Slave）
- 设备型号
- MAC地址
- 优先级
- 状态

## 生成树

### display stp brief
显示生成树协议简要信息。

**输出包含**：
- STP模式（MSTP/RSTP/STP）
- 根桥信息
- 本桥信息
- 端口角色和状态

### display stp
显示详细的生成树信息。

## 配置文件

### display current-configuration
显示当前运行配置。

### display saved-configuration
显示已保存的配置文件。

### display configuration candidate
显示候选配置（如果启用了配置确认功能）。

## 诊断命令

### display device
显示设备硬件组成信息。

**输出包含**：
- 槽位号
- 板卡类型
- 状态
- 子卡信息

### display elabel
显示电子标签信息（硬件条码、序列号等）。

### display transceiver interface [interface-name]
显示光模块信息。

**输出包含**：
- 光模块类型
- 厂商信息
- 波长
- 传输距离
- 温度
- 电压
- 发送光功率
- 接收光功率

**光功率参考**（dBm）：
- 正常：-10 到 0
- 警告：-15 到 -10
- 严重：< -15

### display diagnostic-information
生成诊断信息（用于技术支持）。

## 用户和权限

### display users
显示当前登录用户。

### display access-user
显示接入用户信息。

## 性能统计

### display interface counters
显示接口流量统计。

### display statistics system
显示系统级统计信息。

## License信息

### display license
显示License信息（适用于需要License的型号）。

## 巡检建议

### 基础巡检项目（每日）
1. 系统信息：`display version`
2. CPU使用率：`display cpu-usage`
3. 内存使用：`display memory-usage`
4. 接口状态：`display interface brief`
5. 环境状态：`display temperature`, `display power`, `display fan`
6. 告警信息：`display alarm all`

### 详细巡检项目（每周）
1. 所有基础项目
2. VLAN配置：`display vlan`
3. MAC地址统计：`display mac-address count`
4. ARP表：`display arp statistics`
5. 路由表：`display ip routing-table protocol static`
6. 系统日志：`display logbuffer reverse level warnings`
7. 链路聚合：`display eth-trunk`
8. 生成树：`display stp brief`
9. 堆叠状态：`display stack`（如适用）

### 故障排查项目
1. 详细接口信息：`display interface [有问题的接口]`
2. 接口错误统计：`display interface counters error`
3. 日志分析：`display logbuffer | include Error|Warning`
4. 光模块状态：`display transceiver interface [接口]`
5. 硬件诊断：`display diagnostic-information`
6. 告警详情：`display alarm all`

### 性能分析项目
1. CPU趋势：定期记录`display cpu-usage`
2. 内存趋势：定期记录`display memory-usage`
3. 接口流量：`display interface counters`
4. 温度趋势：定期记录`display temperature`
5. 系统统计：`display statistics system`

## 巡检脚本示例命令组合

### 快速健康检查
```
display version | include uptime
display cpu-usage
display memory-usage
display alarm all
display temperature
```

### 接口健康检查
```
display interface brief
display interface counters error
display transceiver interface brief
display eth-trunk
```

### 网络配置检查
```
display vlan
display mac-address count
display arp statistics
display ip routing-table statistics
```
