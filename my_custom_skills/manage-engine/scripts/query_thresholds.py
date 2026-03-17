#!/usr/bin/env python3
"""
查询阈值配置详情
用法: python query_thresholds.py [resource_id]
"""

import sys
import json
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# 确保 Windows 控制台正确显示中文
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_section(title):
    """打印分节标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def query_threshold_profiles(client):
    """查询所有阈值配置文件"""
    print_section("阈值配置文件 (Threshold Profiles)")

    result = client.list_threshold_profiles()

    if not result:
        print("❌ 查询失败")
        return

    if result.get('response-code') != '4000':
        print(f"❌ 响应码: {result.get('response-code')}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    profiles = result.get('response', {}).get('result', [])

    if not profiles:
        print("未找到阈值配置文件")
        return

    print(f"\n找到 {len(profiles)} 个阈值配置文件:\n")

    for profile in profiles:
        print(f"阈值ID: {profile.get('THRESHOLDID')}")
        print(f"  名称: {profile.get('DISPLAYNAME', 'N/A')}")
        print(f"  描述: {profile.get('DESCRIPTION', 'N/A')}")
        print(f"  类型: {profile.get('TYPE', 'N/A')}")

        # 显示阈值条件
        if 'CRITICALVALUE' in profile:
            print(f"  严重告警条件: {profile.get('CRITICALCONDITION')} {profile.get('CRITICALVALUE')}")
        if 'WARNINGVALUE' in profile:
            print(f"  警告告警条件: {profile.get('WARNINGCONDITION')} {profile.get('WARNINGVALUE')}")
        if 'CLEARVALUE' in profile or 'INFOVALUE' in profile:
            clear_val = profile.get('CLEARVALUE') or profile.get('INFOVALUE')
            clear_cond = profile.get('CLEARCONDITION') or profile.get('INFOCONDITION')
            if clear_val:
                print(f"  恢复告警条件: {clear_cond} {clear_val}")

        # 显示完整数据
        print(f"  完整配置:")
        for key, value in sorted(profile.items()):
            if key not in ['THRESHOLDID', 'DISPLAYNAME', 'DESCRIPTION', 'TYPE',
                          'CRITICALVALUE', 'CRITICALCONDITION', 'WARNINGVALUE',
                          'WARNINGCONDITION', 'CLEARVALUE', 'CLEARCONDITION',
                          'INFOVALUE', 'INFOCONDITION']:
                print(f"    {key}: {value}")
        print()


def query_actions(client):
    """查询所有告警动作"""
    print_section("告警动作 (Actions)")

    result = client.request('ListActions', format='json')

    if not result:
        print("❌ 查询失败")
        return

    if result.get('response-code') != '4000':
        print(f"❌ 响应码: {result.get('response-code')}")
        return

    actions = result.get('response', {}).get('result', [{}])[0].get('Action', [])

    if not actions:
        print("未找到告警动作")
        return

    print(f"\n找到 {len(actions)} 个告警动作:\n")

    for action in actions:
        print(f"动作ID: {action.get('ID')}")
        print(f"  名称: {action.get('NAME')}")
        print(f"  类型: {action.get('TYPE')}")
        print(f"  描述: {action.get('DESCRIPTION', 'N/A')}")

        # 显示其他字段
        for key, value in sorted(action.items()):
            if key not in ['ID', 'NAME', 'TYPE', 'DESCRIPTION']:
                print(f"  {key}: {value}")
        print()


def query_monitor_details(client, resource_id):
    """查询特定监控器的详细信息"""
    print_section(f"监控器详情 (Resource ID: {resource_id})")

    data = client.get_monitor_data(resource_id)

    if not data:
        print("❌ 查询失败")
        return

    if data.get('response-code') != '4000':
        print(f"❌ 响应码: {data.get('response-code')}")
        return

    result = data['response']['result'][0]

    print(f"\n基本信息:")
    print(f"  名称: {result.get('DISPLAYNAME')}")
    print(f"  类型: {result.get('TYPE')}")
    print(f"  状态: {result.get('AVAILABILITYSTATUS')}")
    print(f"  健康状态: {result.get('HEALTHSTATUS')}")

    print(f"\n当前监控值:")
    if 'CPUUTIL' in result:
        print(f"  CPU 利用率: {result.get('CPUUTIL')}%")
    if 'PHYMEMUTIL' in result:
        print(f"  内存利用率: {result.get('PHYMEMUTIL')}%")
    if 'DISKUTIL' in result:
        print(f"  磁盘利用率: {result.get('DISKUTIL')}%")

    # 查找阈值和告警相关字段
    print(f"\n阈值和告警相关字段:")
    found_threshold_fields = False
    for key, value in sorted(result.items()):
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in ['threshold', 'alarm', 'action', 'profile', 'health']):
            print(f"  {key}: {value}")
            found_threshold_fields = True

    if not found_threshold_fields:
        print("  未找到阈值配置字段")

    # 显示完整数据
    print(f"\n完整监控数据:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def query_child_monitors(client, resource_id):
    """查询子监控器"""
    print_section(f"子监控器 (Parent Resource ID: {resource_id})")

    children = client.get_child_monitors(resource_id)

    if not children or children.get('response-code') != '4000':
        print("  无子监控器或无法获取")
        return

    child_list = children['response']['result']

    if not child_list:
        print("  无子监控器")
        return

    print(f"\n找到 {len(child_list)} 个子监控器:\n")

    for child in child_list:
        print(f"子监控器: {child.get('DISPLAYNAME')}")
        print(f"  资源ID: {child.get('RESOURCEID')}")
        print(f"  类型: {child.get('TYPE')}")
        print(f"  健康ID: {child.get('HEALTHID', 'N/A')}")
        print(f"  状态: {child.get('STATUS', 'N/A')}")

        # 显示阈值相关字段
        for key, value in sorted(child.items()):
            key_lower = key.lower()
            if any(keyword in key_lower for keyword in ['threshold', 'alarm', 'action', 'health']):
                print(f"  {key}: {value}")
        print()


def query_current_alarms(client):
    """查询当前活动告警"""
    print_section("当前活动告警")

    alarms = client.list_alarms(type="all")

    if not alarms or alarms.get('response-code') != '4000':
        print("无法获取告警列表")
        return

    alarm_list = alarms.get('response', {}).get('result', [])

    if not alarm_list:
        print("  当前无活动告警")
        return

    print(f"\n找到 {len(alarm_list)} 个活动告警:\n")

    for alarm in alarm_list:
        print(f"监控器: {alarm.get('DISPLAYNAME')}")
        print(f"  资源ID: {alarm.get('RESOURCEID')}")
        print(f"  严重级别: {alarm.get('SEVERITY')}")
        print(f"  消息: {alarm.get('MESSAGE')}")
        print(f"  时间: {alarm.get('ALARMTIME')}")
        print()


def main():
    """主函数"""
    print("="*80)
    print("  ManageEngine 阈值配置查询工具")
    print("="*80)
    print(f"\n服务器: {DEFAULT_URL}")

    if len(sys.argv) > 1:
        resource_id = sys.argv[1]
        print(f"资源ID: {resource_id}")
    else:
        resource_id = None
        print("未指定资源ID，只显示系统配置")

    # 初始化客户端
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    try:
        # 1. 查询阈值配置文件
        query_threshold_profiles(client)

        # 2. 查询告警动作
        query_actions(client)

        # 3. 如果指定了资源ID，查询监控器详情
        if resource_id:
            query_monitor_details(client, resource_id)
            query_child_monitors(client, resource_id)

        # 4. 查询当前活动告警
        query_current_alarms(client)

        print("\n" + "="*80)
        print("  查询完成")
        print("="*80)

        print("\n💡 说明:")
        print("  - ListThresholdProfiles API 在当前版本不可用")
        print("  - 可以通过告警消息查看实际生效的阈值")
        print("  - 使用 configure_alarm() API 可以配置告警阈值")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
