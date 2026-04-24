#!/usr/bin/env python3
"""
配置 CPU 告警阈值
为指定资源配置 CPU 使用率告警（严重: >90%, 警告: >80%）

用法: python set_cpu_alarm.py <resource_id> [critical_threshold] [warning_threshold]
示例:
  python set_cpu_alarm.py 10113263
  python set_cpu_alarm.py 10113263 95 85
"""

import sys
import requests
import urllib3
urllib3.disable_warnings()

# 确保 Windows 控制台正确显示中文
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from manage_engine_api import DEFAULT_URL, DEFAULT_API_KEY

def configure_cpu_alarm(resource_id, critical_threshold=90, warning_threshold=80):
    """
    为指定资源配置 CPU 告警阈值

    方法: 通过 Web 界面手动配置
    因为 API 的 configurealarms 端点需要复杂的条件格式，
    建议通过 Web 界面配置自定义阈值更可靠。
    """

    print("="*80)
    print("  CPU 告警阈值配置向导")
    print("="*80)

    # 获取资源信息
    from manage_engine_api import AppManagerClient
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    print("\n📊 正在获取资源信息...")
    data = client.get_monitor_data(resource_id)

    if not data or data.get('response-code') != '4000':
        print("❌ 无法获取资源信息")
        return False

    result = data['response']['result'][0]
    display_name = result.get('DISPLAYNAME')
    cpu_util = result.get('CPUUTIL', 'N/A')

    print("\n资源信息:")
    print(f"  名称: {display_name}")
    print(f"  资源ID: {resource_id}")
    print(f"  当前 CPU: {cpu_util}%")

    # 方法1: 应用默认阈值模板
    print("\n" + "="*80)
    print("方法1: 应用系统默认阈值模板（快速）")
    print("="*80)

    url = f"{DEFAULT_URL}/AppManager/xml/configurealarms"
    params = {
        'apikey': DEFAULT_API_KEY,
        'resourceid': resource_id,
        'attributeid': '708',  # CPU 利用率属性 ID
        'thresholdid': '1',    # 默认阈值模板
        'requesttype': '1',
        'overrideConf': 'true'
    }

    print("\n正在应用默认阈值模板...")
    try:
        r = requests.post(url, data=params, verify=False, timeout=30)
        if r.status_code == 200 and '4000' in r.text:
            print("✅ 成功应用默认阈值模板到 CPU 属性")
            print("   (系统会使用默认的告警阈值)")
        else:
            print("⚠️  应用默认模板时出现问题")
            print(f"   响应: {r.text[:200]}")
    except Exception as e:
        print(f"❌ 应用失败: {e}")

    # 方法2: Web 界面配置自定义阈值
    print("\n" + "="*80)
    print("方法2: Web 界面配置自定义阈值（推荐，精确控制）")
    print("="*80)

    print(f"\n要配置精确的 CPU > {critical_threshold}% 告警，请按以下步骤操作:")
    print("\n1. 访问资源详情页:")
    print(f"   https://192.168.129.132:8443/showresource.do?resourceid={resource_id}")

    print("\n2. 找到 'CPU利用率' 指标并点击")

    print("\n3. 在属性详情页，点击 'Add Threshold and Associate' 或 'Associate Threshold'")

    print("\n4. 配置阈值:")
    print("   a) 如果选择创建新阈值:")
    print("      - Threshold Name: CPU_Custom_Threshold")
    print(f"      - Critical: 值 = {critical_threshold}, 条件 = 大于(>)")
    print(f"      - Warning: 值 = {warning_threshold}, 条件 = 大于(>)")
    print("      - Consecutive Polls: 2 (连续2次超过才告警)")

    print("\n   b) 或者选择现有的阈值配置文件，然后关联")

    print("\n5. 保存配置")

    # 方法3: 通过阈值配置管理页面
    print("\n" + "="*80)
    print("方法3: 全局阈值配置（适合批量应用）")
    print("="*80)

    print("\n1. 进入阈值配置管理:")
    print("   https://192.168.129.132:8443/admin/AdminConfiguration.do")
    print("   → Threshold and Availability → Threshold Settings")

    print("\n2. 创建新的阈值配置文件:")
    print("   - 点击 'Add Threshold Profile'")
    print("   - 选择监控类型: Linux")
    print("   - 配置 CPU 利用率阈值:")
    print(f"     * Critical: > {critical_threshold}%")
    print(f"     * Warning: > {warning_threshold}%")

    print("\n3. 应用到资源:")
    print("   - 可以应用到单个资源")
    print("   - 或应用到整个监控组")

    # 验证
    print("\n" + "="*80)
    print("验证配置")
    print("="*80)

    print("\n配置完成后，可以:")
    print("1. 等待5-10分钟（至少2个轮询周期）")
    print("2. 访问 Alarms → Alarm Settings 查看配置")
    print("3. 在资源详情页查看阈值是否已关联")
    print("4. 可以手动触发高 CPU 负载来测试告警")

    return True

def main():
    if len(sys.argv) < 2:
        print("用法: python set_cpu_alarm.py <resource_id> [critical_threshold] [warning_threshold]")
        print("\n示例:")
        print("  python set_cpu_alarm.py 10113263")
        print("  python set_cpu_alarm.py 10113263 95 85")
        print("\n说明:")
        print("  - 默认严重阈值: 90%")
        print("  - 默认警告阈值: 80%")
        sys.exit(1)

    resource_id = sys.argv[1]
    critical = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    warning = int(sys.argv[3]) if len(sys.argv) > 3 else 80

    success = configure_cpu_alarm(resource_id, critical, warning)

    print("\n" + "="*80)
    if success:
        print("  ✅ 配置向导完成")
    else:
        print("  ❌ 配置过程中出现错误")
    print("="*80 + "\n")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
