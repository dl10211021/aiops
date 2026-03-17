#!/usr/bin/env python3
"""
查看阈值模板（阈值规则）
用法: python list_threshold_templates.py [--detail] [threshold_id]
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY
import json


def list_all_templates(client, show_detail=False):
    """列出所有阈值模板"""
    print("="*100)
    print("  系统中的阈值模板 (Threshold Templates)")
    print("="*100)

    result = client.request('threshold', format='json', method='GET')

    if not result or result.get('response-code') != '4000':
        print("❌ 无法获取阈值模板")
        return []

    # 响应结构是 response -> result -> [阈值列表]
    result_data = result.get('response', {}).get('result', [])
    if not result_data:
        thresholds = []
    elif isinstance(result_data, list):
        thresholds = result_data
    else:
        thresholds = [result_data]

    print(f"\n找到 {len(thresholds)} 个阈值模板\n")

    if not show_detail:
        # 简要列表
        print(f"{'序号':<6} {'阈值ID':<12} {'模板名称':<40} {'描述':<50}")
        print("-" * 100)

        for i, th in enumerate(thresholds, 1):
            th_id = th.get('THRESHOLDID', 'N/A')
            th_name = th.get('THRESHOLDNAME', 'N/A')
            desc = th.get('DESCRIPTION', '')
            if len(desc) > 47:
                desc = desc[:47] + '...'

            print(f"{i:<6} {th_id:<12} {th_name:<40} {desc:<50}")
    else:
        # 详细信息
        for i, th in enumerate(thresholds, 1):
            print(f"\n{i}. {th.get('THRESHOLDNAME')}")
            print(f"   阈值ID: {th.get('THRESHOLDID')}")
            print(f"   描述: {th.get('DESCRIPTION', '无')}")

            # 严重告警
            print(f"\n   严重告警 (Critical):")
            print(f"     条件: {th.get('CRITICALTHRESHOLDCONDITION', 'N/A')} {th.get('CRITICALTHRESHOLDVALUE', 'N/A')}")
            print(f"     消息: {th.get('CRITICALTHRESHOLDMESSAGE', '无')}")
            print(f"     重试次数: {th.get('CRITICALPOLLSTORETRY', '使用全局默认')}")
            print(f"     最小重试: {th.get('MINIMUMCRITICALPOLLSTORETRY', '使用全局默认')}")

            # 警告告警
            print(f"\n   警告告警 (Warning):")
            print(f"     条件: {th.get('WARNINGTHRESHOLDCONDITION', 'N/A')} {th.get('WARNINGTHRESHOLDVALUE', 'N/A')}")
            print(f"     消息: {th.get('WARNINGTHRESHOLDMESSAGE', '无')}")
            print(f"     重试次数: {th.get('WARNINGPOLLSTORETRY', '使用全局默认')}")
            print(f"     最小重试: {th.get('MINIMUMWARNINGPOLLSTORETRY', '使用全局默认')}")

            # 恢复告警
            print(f"\n   恢复告警 (Clear):")
            print(f"     条件: {th.get('CLEARTHRESHOLDCONDITION', 'N/A')} {th.get('CLEARTHRESHOLDVALUE', 'N/A')}")
            print(f"     消息: {th.get('CLEARTHRESHOLDMESSAGE', '无')}")
            print(f"     重试次数: {th.get('CLEARPOLLSTORETRY', '使用全局默认')}")
            print(f"     最小重试: {th.get('MINIMUMCLEARPOLLSTORETRY', '使用全局默认')}")

            print("-" * 100)

    return thresholds


def show_template_detail(client, threshold_id):
    """显示特定阈值模板的详细信息"""
    print("="*100)
    print(f"  阈值模板详情 (ID: {threshold_id})")
    print("="*100)

    result = client.request('threshold', format='json', method='GET')

    if not result or result.get('response-code') != '4000':
        print("❌ 无法获取阈值模板")
        return

    result_data = result.get('response', {}).get('result', [])
    if not result_data:
        thresholds = []
    elif isinstance(result_data, list):
        thresholds = result_data
    else:
        thresholds = [result_data]

    # 查找指定ID的模板
    template = None
    for th in thresholds:
        if th.get('THRESHOLDID') == threshold_id:
            template = th
            break

    if not template:
        print(f"❌ 未找到阈值ID为 {threshold_id} 的模板")
        return

    print(f"\n模板名称: {template.get('THRESHOLDNAME')}")
    print(f"阈值ID: {template.get('THRESHOLDID')}")
    print(f"描述: {template.get('DESCRIPTION', '无')}")

    print(f"\n{'='*100}")
    print("严重告警配置 (Critical)")
    print(f"{'='*100}")
    print(f"  条件: {template.get('CRITICALTHRESHOLDCONDITION', 'N/A')} {template.get('CRITICALTHRESHOLDVALUE', 'N/A')}")
    print(f"  消息: {template.get('CRITICALTHRESHOLDMESSAGE', '无')}")
    print(f"  重试次数: {template.get('CRITICALPOLLSTORETRY', '使用全局默认')}")
    print(f"  最小重试: {template.get('MINIMUMCRITICALPOLLSTORETRY', '使用全局默认')}")

    # 如果有次要条件
    if template.get('CRITICALCONDITIONJOINER'):
        print(f"  次要条件连接符: {template.get('CRITICALCONDITIONJOINER')}")
        if template.get('SECONDARYCRITICALTHRESHOLDCONDITION'):
            print(f"  次要条件: {template.get('SECONDARYCRITICALTHRESHOLDCONDITION')} {template.get('SECONDARYCRITICALTHRESHOLDVALUE')}")

    print(f"\n{'='*100}")
    print("警告告警配置 (Warning)")
    print(f"{'='*100}")
    print(f"  条件: {template.get('WARNINGTHRESHOLDCONDITION', 'N/A')} {template.get('WARNINGTHRESHOLDVALUE', 'N/A')}")
    print(f"  消息: {template.get('WARNINGTHRESHOLDMESSAGE', '无')}")
    print(f"  重试次数: {template.get('WARNINGPOLLSTORETRY', '使用全局默认')}")
    print(f"  最小重试: {template.get('MINIMUMWARNINGPOLLSTORETRY', '使用全局默认')}")

    if template.get('WARNINGCONDITIONJOINER'):
        print(f"  次要条件连接符: {template.get('WARNINGCONDITIONJOINER')}")
        if template.get('SECONDARYWARNINGTHRESHOLDCONDITION'):
            print(f"  次要条件: {template.get('SECONDARYWARNINGTHRESHOLDCONDITION')} {template.get('SECONDARYWARNINGTHRESHOLDVALUE')}")

    print(f"\n{'='*100}")
    print("恢复告警配置 (Clear)")
    print(f"{'='*100}")
    print(f"  条件: {template.get('CLEARTHRESHOLDCONDITION', 'N/A')} {template.get('CLEARTHRESHOLDVALUE', 'N/A')}")
    print(f"  消息: {template.get('CLEARTHRESHOLDMESSAGE', '无')}")
    print(f"  重试次数: {template.get('CLEARPOLLSTORETRY', '使用全局默认')}")
    print(f"  最小重试: {template.get('MINIMUMCLEARPOLLSTORETRY', '使用全局默认')}")

    if template.get('INFOCONDITIONJOINER'):
        print(f"  次要条件连接符: {template.get('INFOCONDITIONJOINER')}")
        if template.get('SECONDARYINFOTHRESHOLDCONDITION'):
            print(f"  次要条件: {template.get('SECONDARYINFOTHRESHOLDCONDITION')} {template.get('SECONDARYINFOTHRESHOLDVALUE')}")

    # 显示其他高级配置
    if template.get('ADAPTIVEBASEFORMULATYPE'):
        print(f"\n{'='*100}")
        print("自适应配置 (Adaptive)")
        print(f"{'='*100}")
        print(f"  公式类型: {template.get('ADAPTIVEBASEFORMULATYPE')}")
        print(f"  基准周: {template.get('ADAPTIVEBASEWEEK', 'N/A')}")
        print(f"  百分比: {template.get('ADAPTIVEPERCENTAGE', 'N/A')}")

    # 显示完整JSON（可选）
    print(f"\n{'='*100}")
    print("完整配置 (JSON)")
    print(f"{'='*100}")
    print(json.dumps(template, indent=2, ensure_ascii=False))


def search_templates(client, keyword):
    """搜索阈值模板"""
    print("="*100)
    print(f"  搜索阈值模板: '{keyword}'")
    print("="*100)

    result = client.request('threshold', format='json', method='GET')

    if not result or result.get('response-code') != '4000':
        print("❌ 无法获取阈值模板")
        return

    result_data = result.get('response', {}).get('result', [])
    if not result_data:
        thresholds = []
    elif isinstance(result_data, list):
        thresholds = result_data
    else:
        thresholds = [result_data]

    # 搜索
    keyword_lower = keyword.lower()
    matched = []

    for th in thresholds:
        name = th.get('THRESHOLDNAME', '').lower()
        desc = th.get('DESCRIPTION', '').lower()
        th_id = th.get('THRESHOLDID', '').lower()

        if keyword_lower in name or keyword_lower in desc or keyword_lower in th_id:
            matched.append(th)

    if not matched:
        print(f"\n未找到包含 '{keyword}' 的阈值模板")
        return

    print(f"\n找到 {len(matched)} 个匹配的阈值模板:\n")
    print(f"{'序号':<6} {'阈值ID':<12} {'模板名称':<40} {'描述':<50}")
    print("-" * 100)

    for i, th in enumerate(matched, 1):
        th_id = th.get('THRESHOLDID', 'N/A')
        th_name = th.get('THRESHOLDNAME', 'N/A')
        desc = th.get('DESCRIPTION', '')
        if len(desc) > 47:
            desc = desc[:47] + '...'

        print(f"{i:<6} {th_id:<12} {th_name:<40} {desc:<50}")


def print_usage():
    """打印使用说明"""
    print("""
用法: python list_threshold_templates.py [选项]

选项:
  (无参数)          列出所有阈值模板（简要）
  --detail          列出所有阈值模板（详细）
  --id <阈值ID>     显示特定阈值模板的详细信息
  --search <关键词>  搜索阈值模板

示例:
  # 列出所有模板（简要）
  python list_threshold_templates.py

  # 列出所有模板（详细）
  python list_threshold_templates.py --detail

  # 查看特定模板
  python list_threshold_templates.py --id 10000099

  # 搜索包含"CPU"的模板
  python list_threshold_templates.py --search CPU

常用阈值模板:
  - CPU 使用率模板
  - 内存使用率模板
  - 磁盘使用率模板
  - SWAP 内存使用率模板
  - 网络接口状态模板
""")


def main():
    """主函数"""
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    if len(sys.argv) == 1:
        # 无参数：简要列表
        list_all_templates(client, show_detail=False)

    elif len(sys.argv) == 2:
        if sys.argv[1] == '--detail':
            # 详细列表
            list_all_templates(client, show_detail=True)
        elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print_usage()
        else:
            print("❌ 无效参数，使用 --help 查看帮助")

    elif len(sys.argv) == 3:
        if sys.argv[1] == '--id':
            # 查看特定模板
            show_template_detail(client, sys.argv[2])
        elif sys.argv[1] == '--search':
            # 搜索模板
            search_templates(client, sys.argv[2])
        else:
            print("❌ 无效参数，使用 --help 查看帮助")

    else:
        print("❌ 参数错误，使用 --help 查看帮助")

    print("\n" + "="*100)
    print("  查询完成")
    print("="*100)

    print("\n💡 提示:")
    print("  - 使用阈值ID配置告警: python setup_alarms.py <resource_id> <action_id>")
    print("  - 配置时在 configure_alarm() 中指定 threshold_id 参数")


if __name__ == "__main__":
    main()
