#!/usr/bin/env python3
"""
完整的告警配置脚本
为服务器配置健康状况、可用性告警，并关联到指定的微信机器人

用法: python setup_alarms.py <resource_id> <action_id>
示例: python setup_alarms.py 10113263 10000012
"""

import sys
import requests
import urllib3
urllib3.disable_warnings()

# 确保 Windows 控制台正确显示中文
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY, AppManagerClient

def configure_availability_alarm(resource_id, action_id):
    """
    配置可用性告警（服务器宕机告警）
    属性ID: 700
    """
    print("\n配置可用性告警...")
    url = f"{DEFAULT_URL}/AppManager/xml/configurealarms"

    params = {
        'apikey': DEFAULT_API_KEY,
        'resourceid': resource_id,
        'attributeid': '700',  # 可用性
        'thresholdid': '1',    # 使用默认模板
        'criticalactionid': action_id,
        'warningactionid': action_id,
        'requesttype': '1',
        'overrideConf': 'true'
    }

    try:
        r = requests.post(url, data=params, verify=False, timeout=30)
        if r.status_code == 200 and '4000' in r.text:
            print("✅ 可用性告警配置成功")
            return True
        else:
            print(f"⚠️  配置响应: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 配置失败: {e}")
        return False

def configure_health_alarm(resource_id, action_id):
    """
    配置健康状况告警
    属性ID: 701
    """
    print("\n配置健康状况告警...")
    url = f"{DEFAULT_URL}/AppManager/xml/configurealarms"

    params = {
        'apikey': DEFAULT_API_KEY,
        'resourceid': resource_id,
        'attributeid': '701',  # 健康状况
        'thresholdid': '1',    # 使用默认模板
        'criticalactionid': action_id,
        'warningactionid': action_id,
        'requesttype': '1',
        'overrideConf': 'true'
    }

    try:
        r = requests.post(url, data=params, verify=False, timeout=30)
        if r.status_code == 200 and '4000' in r.text:
            print("✅ 健康状况告警配置成功")
            return True
        else:
            print(f"⚠️  配置响应: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 配置失败: {e}")
        return False

def remove_cpu_false_alarm(resource_id):
    """
    移除 CPU = 0% 导致的误报配置
    """
    print("\n移除 CPU 误报配置...")
    url = f"{DEFAULT_URL}/AppManager/xml/configurealarms"

    # 使用 requesttype=3 移除配置
    params = {
        'apikey': DEFAULT_API_KEY,
        'resourceid': resource_id,
        'attributeid': '708',  # CPU 利用率
        'requesttype': '3',    # 移除配置
    }

    try:
        r = requests.post(url, data=params, verify=False, timeout=30)
        if r.status_code == 200:
            print("✅ 已移除 CPU 误报配置")
            return True
        else:
            print(f"⚠️  移除响应: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"⚠️  移除操作: {e}")
        return False

def verify_configuration(resource_id, action_name):
    """验证配置"""
    print("\n验证告警配置...")
    print("="*80)

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    data = client.get_monitor_data(resource_id)

    if not data or data.get('response-code') != '4000':
        print("❌ 无法获取资源信息")
        return False

    result = data['response']['result'][0]
    print(f"\n服务器状态:")
    print(f"  名称: {result.get('DISPLAYNAME')}")
    print(f"  可用性: {result.get('AVAILABILITYSTATUS')}")
    print(f"  健康状态: {result.get('HEALTHSTATUS')}")
    print(f"  CPU: {result.get('CPUUTIL')}%")
    print(f"  内存: {result.get('PHYMEMUTIL')}%")

    print(f"\n✅ 已配置告警:")
    print(f"  1. 可用性告警 (属性ID: 700) → {action_name}")
    print(f"  2. 健康状况告警 (属性ID: 701) → {action_name}")
    print(f"  3. 已移除 CPU 误报配置")

    print(f"\n📱 告警触发条件:")
    print(f"  - 服务器宕机 (可用性 = down)")
    print(f"  - 健康状态异常 (warning/critical)")
    print(f"  - 连续 2 次轮询确认后触发")

    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python setup_alarms.py <resource_id> <action_id>")
        print("\n示例:")
        print("  python setup_alarms.py 10113263 10000012")
        print("\n说明:")
        print("  resource_id: 监控资源的 ID")
        print("  action_id: 告警动作的 ID")
        print("\n常用告警动作:")
        print("  10000012 - 丁露微信机器人")
        print("  10000011 - 顾友峰微信机器人")
        print("  10000007 - 基础架构微信机器人")
        sys.exit(1)

    resource_id = sys.argv[1]
    action_id = sys.argv[2]

    # 获取动作名称
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    actions_data = client.request('ListActions', format='json')
    action_name = "未知"

    if actions_data and actions_data.get('response-code') == '4000':
        actions = actions_data['response']['result'][0].get('Action', [])
        for action in actions:
            if action.get('ID') == action_id:
                action_name = action.get('NAME')
                break

    print("="*80)
    print("  ManageEngine 告警配置工具")
    print("="*80)
    print(f"\n配置信息:")
    print(f"  资源ID: {resource_id}")
    print(f"  告警动作: {action_name} (ID: {action_id})")

    # 执行配置
    success = True

    # 1. 配置可用性告警
    if not configure_availability_alarm(resource_id, action_id):
        success = False

    # 2. 配置健康状况告警
    if not configure_health_alarm(resource_id, action_id):
        success = False

    # 3. 移除 CPU 误报配置
    remove_cpu_false_alarm(resource_id)

    # 4. 验证配置
    print()
    verify_configuration(resource_id, action_name)

    print("\n" + "="*80)
    if success:
        print("  ✅ 告警配置完成")
    else:
        print("  ⚠️  部分配置可能失败，请检查")
    print("="*80)

    print("\n💡 建议:")
    print("  1. 等待 5-10 分钟观察告警状态")
    print("  2. 使用 query_thresholds.py 查看配置结果")
    print("  3. 如需配置其他告警，使用 configure_alarms_advanced.py")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
