#!/usr/bin/env python3
"""
删除监控资源脚本
用法:
  python delete_monitor.py <IP地址或显示名称>
  python delete_monitor.py <资源ID> --id

示例:
  python delete_monitor.py 192.168.130.45
  python delete_monitor.py 10113198 --id
"""

import sys
import json
import logging
from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

# 确保 Windows 控制台正确显示中文
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DeleteMonitor')

def delete_by_resource_id(client, resource_id):
    """直接通过资源 ID 删除"""
    print(f"正在删除资源 ID: {resource_id}")
    result = client.delete_monitor(resource_id)

    if result and result.get('response-code') == '4000':
        print(f"✅ 成功删除监控资源 (ID: {resource_id})")
        return True
    else:
        print("❌ 删除失败")
        if result:
            print(f"返回信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return False

def delete_by_identifier(client, identifier):
    """通过 IP 地址或显示名称删除"""
    # 1. 查找资源
    print(f"正在搜索监控资源: {identifier}")
    data = client.list_monitors()

    if not data or 'response' not in data or 'result' not in data['response']:
        print("❌ 无法获取监控列表")
        return False

    monitors = data['response']['result']
    target = [m for m in monitors if
              identifier in str(m.get('DISPLAYNAME', '')) or
              identifier in str(m.get('HOST', '')) or
              identifier in str(m.get('HOSTIP', ''))]

    if not target:
        print(f"❌ 未找到匹配的监控资源: {identifier}")
        return False

    if len(target) > 1:
        print(f"⚠️  找到 {len(target)} 个匹配的资源:")
        for i, m in enumerate(target, 1):
            print(f"  {i}. {m.get('DISPLAYNAME')} (ID: {m.get('RESOURCEID')}, IP: {m.get('HOSTIP')})")
        print("\n请使用更精确的标识符")
        return False

    # 2. 显示资源信息
    resource = target[0]
    resource_id = resource.get('RESOURCEID')
    display_name = resource.get('DISPLAYNAME')
    host_ip = resource.get('HOSTIP')
    resource_type = resource.get('TYPESHORTNAME')

    print("\n找到监控资源:")
    print(f"  名称: {display_name}")
    print(f"  类型: {resource_type}")
    print(f"  IP: {host_ip}")
    print(f"  资源ID: {resource_id}")

    # 3. 确认删除
    confirm = input("\n确认删除此监控? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', '是']:
        print("❌ 取消删除操作")
        return False

    # 4. 执行删除
    result = client.delete_monitor(resource_id)

    if result and result.get('response-code') == '4000':
        print(f"✅ 成功删除监控: {display_name} ({host_ip})")

        # 5. 验证删除
        print("验证删除结果...")
        verify_data = client.list_monitors()
        if verify_data:
            verify_monitors = verify_data['response']['result']
            still_exists = [m for m in verify_monitors if m.get('RESOURCEID') == resource_id]
            if not still_exists:
                print("✅ 验证通过: 资源已从监控列表中移除")
            else:
                print("⚠️  警告: 资源可能仍存在于监控列表中")

        return True
    else:
        print("❌ 删除失败")
        if result:
            print(f"返回信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python delete_monitor.py <IP地址或显示名称>")
        print("  python delete_monitor.py <资源ID> --id")
        print("\n示例:")
        print("  python delete_monitor.py 192.168.130.45")
        print("  python delete_monitor.py 10113198 --id")
        sys.exit(1)

    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)

    # 检查是否使用 --id 参数
    if len(sys.argv) == 3 and sys.argv[2] == '--id':
        success = delete_by_resource_id(client, sys.argv[1])
    else:
        success = delete_by_identifier(client, sys.argv[1])

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()