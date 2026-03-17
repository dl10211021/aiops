#!/usr/bin/env python3
"""
阈值告警配置指南和辅助工具
用法: python configure_threshold.py <resource_id>
示例: python configure_threshold.py 10113263
"""

import sys
import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# 确保 Windows 控制台正确显示中文
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def show_resource_info(client, resource_id):
    """显示资源的详细监控信息"""
    print("\n" + "="*80)
    print(f"  资源 {resource_id} 的监控属性和阈值配置指南")
    print("="*80)

    # 获取监控数据
    data = client.get_monitor_data(resource_id)
    if not data or data.get('response-code') != '4000':
        print("❌ 无法获取监控数据")
        return False

    result = data['response']['result'][0]
    display_name = result.get('DISPLAYNAME')
    resource_type = result.get('TYPESHORTNAME')
    last_polled = result.get('LASTPOLLEDTIME', '未轮询')

    print(f"\n📊 资源基本信息:")
    print(f"  名称: {display_name}")
    print(f"  类型: {resource_type}")
    print(f"  资源ID: {resource_id}")
    print(f"  最后轮询: {last_polled}")

    # 显示当前性能指标
    cpu = result.get('CPUUTIL', 'N/A')
    mem = result.get('PHYMEMUTIL', 'N/A')
    disk = result.get('DISKUTIL', 'N/A')

    print(f"\n📈 当前性能指标:")
    print(f"  CPU 使用率: {cpu}%")
    print(f"  内存使用率: {mem}%")
    print(f"  磁盘使用率: {disk}%")

    # 获取所有监控属性
    attributes = result.get('Attribute', [])
    health_attr_id = result.get('HEALTHATTRIBUTEID')
    avail_attr_id = result.get('AVAILABILITYATTRIBUTEID')

    print(f"\n🔍 监控属性列表 ({len(attributes)} 个):")
    print("-" * 80)

    # 重要属性
    important_attrs = []
    for attr in attributes:
        attr_name = attr.get('DISPLAYNAME', '')
        if any(keyword in attr_name for keyword in ['CPU', 'cpu', '内存', 'Memory', '磁盘', 'Disk']):
            important_attrs.append(attr)

    if important_attrs:
        print("\n  🔴 关键性能指标:")
        for attr in important_attrs:
            attr_id = attr.get('AttributeID')
            name = attr.get('DISPLAYNAME')
            value = attr.get('Value', 'N/A')
            units = attr.get('Units', '')
            print(f"    [{attr_id}] {name}: {value}{units}")

    # 显示部分其他属性
    print("\n  📋 其他监控属性（前10个）:")
    other_attrs = [a for a in attributes if a not in important_attrs][:10]
    for attr in other_attrs:
        attr_id = attr.get('AttributeID')
        name = attr.get('DISPLAYNAME')
        value = attr.get('Value', 'N/A')
        units = attr.get('Units', '')
        print(f"    [{attr_id}] {name}: {value}{units}")

    if len(attributes) > len(important_attrs) + 10:
        print(f"    ... 还有 {len(attributes) - len(important_attrs) - 10} 个属性")

    print(f"\n  🏥 特殊属性:")
    print(f"    []{health_attr_id}] 健康状态 (Health Status)")
    print(f"    [{avail_attr_id}] 可用性 (Availability)")

    return True

def show_threshold_guide(resource_id):
    """显示阈值配置指南"""
    print("\n" + "="*80)
    print("  🔔 阈值告警配置指南")
    print("="*80)

    print("\n📌 方法1: Web 界面配置（推荐）")
    print("-" * 80)
    print(f"\n1. 访问资源详情页:")
    print(f"   https://192.168.129.132:8443/showresource.do?resourceid={resource_id}")

    print(f"\n2. 配置步骤:")
    print("   a) 在资源详情页，找到要配置阈值的性能指标（如 CPU 利用率）")
    print("   b) 点击该指标名称，进入属性详情页")
    print("   c) 在属性详情页，点击 'Associate Threshold' 或 '关联阈值'")
    print("   d) 选择合适的阈值配置文件（Default 或自定义）")
    print("   e) 保存配置")

    print(f"\n3. 推荐的阈值设置:")
    print("   CPU 利用率:")
    print("     - Warning (警告):  > 80%")
    print("     - Critical (严重): > 90%")
    print("\n   内存利用率:")
    print("     - Warning (警告):  > 85%")
    print("     - Critical (严重): > 95%")
    print("\n   磁盘利用率:")
    print("     - Warning (警告):  > 80%")
    print("     - Critical (严重): > 90%")

    print("\n\n📌 方法2: 创建自定义阈值配置文件")
    print("-" * 80)
    print("\n如果默认的阈值不满足需求，可以创建自定义阈值:")
    print("1. 进入 Admin → Threshold Configuration")
    print("2. 点击 'Add Threshold Profile'")
    print("3. 选择监控类型（如 Linux Server）")
    print("4. 设置各项指标的告警阈值")
    print("5. 保存并应用到资源")

    print("\n\n📌 方法3: 批量应用阈值")
    print("-" * 80)
    print("\n如果有多台相同类型的服务器:")
    print("1. 创建一个阈值配置文件")
    print("2. 在监控组级别应用该配置文件")
    print("3. 所有组内的服务器将自动继承阈值配置")

    print("\n\n📌 验证配置")
    print("-" * 80)
    print(f"\n配置完成后，可以通过以下方式验证:")
    print(f"1. 访问资源详情页查看阈值是否已关联")
    print(f"2. 等待下次轮询（5分钟），观察告警是否正常触发")
    print(f"3. 在 Alarms → All Alarms 中查看告警记录")

def main():
    if len(sys.argv) < 2:
        print("用法: python configure_threshold.py <resource_id>")
        print("示例: python configure_threshold.py 10113263")
        print("\n说明: 显示资源的监控属性和阈值配置指南")
        sys.exit(1)

    resource_id = sys.argv[1]
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    # 显示资源信息
    success = show_resource_info(client, resource_id)

    if not success:
        sys.exit(1)

    # 显示配置指南
    show_threshold_guide(resource_id)

    print("\n" + "="*80)
    print("  ✅ 配置指南已显示完毕")
    print("="*80)
    print(f"\n💡 提示: 现在可以访问 Web 界面完成阈值配置")
    print(f"   https://192.168.129.132:8443/showresource.do?resourceid={resource_id}\n")

if __name__ == "__main__":
    main()
