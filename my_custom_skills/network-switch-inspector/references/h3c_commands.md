# H3C交换机命令参考

本文档提供H3C交换机常用巡检命令的详细说明。

## 系统信息

### display version
显示设备版本信息、硬件信息、系统运行时间等。

**输出包含**：
- 设备型号
- 软件版本号
- 硬件版本号
- BootWare版本
- 设备序列号
- 系统运行时间

**示例输出**：
```
H3C Comware Software, Version 7.1.070, Release 6555P06
Copyright (c) 2004-2021 New H3C Technologies Co., Ltd. All rights reserved.
H3C S5560S-EI uptime is 180 days, 5 hours, 23 minutes
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

### display memory
显示内存使用情况。

**输出包含**：
- 总内存容量
- 已用内存
- 空闲内存
- 内存使用率

## 接口管理

### display interface brief
显示所有接口的简要信息。

**输出包含**：
- 接口名称
- 物理状态（UP/DOWN）
- 协议状态（UP/DOWN）
- 接口描述
- 速率和双工模式

**示例输出**：
```
Interface            Link Speed   Duplex Type   PVID Description
GE1/0/1              UP   1G      F      copper 1    To-Core-Switch
GE1/0/2              DOWN auto    auto   copper 1
```

### display interface [interface-name]
显示指定接口的详细信息。

**输出包含**：
- 接口状态
- 物理参数
- 流量统计
- 错误统计
- 最后状态变更时间

**关键指标**：
- Input errors：输入错误包数
- CRC errors：CRC错误
- Output errors：输出错误
- Collisions：冲突数

## VLAN管理

### display vlan
显示所有VLAN配置信息。

**输出包含**：
- VLAN ID
- VLAN名称
- VLAN类型
- 包含的接口
- 状态

### display vlan [vlan-id]
显示指定VLAN的详细信息。

## MAC地址表

### display mac-address
显示MAC地址表。

**输出包含**：
- MAC地址
- VLAN ID
- 学习类型（动态/静态）
- 接口
- 老化时间

**常用参数**：
- `display mac-address interface [interface-name]` - 显示指定接口的MAC
- `display mac-address vlan [vlan-id]` - 显示指定VLAN的MAC
- `display mac-address count` - 显示MAC地址统计

## ARP表

### display arp
显示ARP表信息。

**输出包含**：
- IP地址
- MAC地址
- VLAN ID
- 接口
- 老化时间
- 类型（动态/静态）

## 路由表

### display ip routing-table
显示IP路由表。

**输出包含**：
- 目标网络
- 子网掩码
- 下一跳
- 出接口
- 协议类型
- 优先级/开销

## 日志管理

### display logbuffer
显示系统日志缓冲区内容。

**日志级别**：
- 0 - Emergency：紧急
- 1 - Alert：告警
- 2 - Critical：严重
- 3 - Error：错误
- 4 - Warning：警告
- 5 - Notice：通知
- 6 - Informational：信息
- 7 - Debug：调试

**常用参数**：
- `display logbuffer reverse` - 反向显示（最新在前）
- `display logbuffer | include Error` - 过滤错误日志
- `display logbuffer level 4` - 只显示警告及以上级别

## 环境监控

### display environment
显示设备环境信息（温度、电源、风扇等）。

**输出包含**：
- 温度传感器读数
- 电源模块状态
- 风扇状态和转速
- 告警信息

**温度阈值参考**：
- 正常：< 50°C
- 警告：50-65°C
- 严重：> 65°C

### display power
显示电源模块状态。

**输出包含**：
- 电源模块编号
- 状态（正常/异常）
- 型号
- 额定功率

### display fan
显示风扇状态。

**输出包含**：
- 风扇编号
- 状态（正常/异常）
- 转速（RPM）

## 链路聚合

### display link-aggregation summary
显示链路聚合组摘要信息。

### display link-aggregation verbose
显示链路聚合组详细信息。

## 生成树

### display stp brief
显示生成树协议简要信息。

**输出包含**：
- STP模式
- 根桥ID
- 本桥ID
- 端口角色和状态

## 配置文件

### display current-configuration
显示当前运行配置。

### display saved-configuration
显示已保存的配置。

## 诊断命令

### display diagnostic-information
显示诊断信息（用于故障排查）。

### display device
显示设备硬件信息。

### display transceiver interface [interface-name]
显示光模块信息（光功率、温度等）。

## 巡检建议

### 基础巡检项目
1. 系统信息：`display version`
2. CPU使用率：`display cpu-usage`
3. 内存使用：`display memory`
4. 接口状态：`display interface brief`
5. 环境状态：`display environment`

### 详细巡检项目
1. 所有基础项目
2. VLAN配置：`display vlan`
3. MAC地址表：`display mac-address count`
4. ARP表：`display arp`
5. 路由表：`display ip routing-table`
6. 系统日志：`display logbuffer reverse | include Error|Warning`
7. 链路聚合：`display link-aggregation summary`
8. 生成树：`display stp brief`

### 故障排查项目
1. 详细接口信息：`display interface`
2. 接口错误统计
3. 日志分析（错误和告警）
4. 光模块状态：`display transceiver interface`
5. 诊断信息：`display diagnostic-information`
