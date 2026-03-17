"""Fix remaining mojibake in headless section of agent.py"""
filepath = r"D:\AI\skillops - 20260225\core\agent.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the second SYSTEM_PROMPT block (headless_agent_chat)
lines = content.split('\n')

# Find exact boundaries
block_start = None
block_end = None
for i, line in enumerate(lines):
    if i >= 258 and i <= 262 and 'SYSTEM_PROMPT = f"""' in line:
        block_start = i
        break

if block_start:
    for i in range(block_start + 3, len(lines)):
        if lines[i].strip() == '"""' and i > block_start + 5:
            block_end = i
            break

    print(f"Second block: lines {block_start+1} to {block_end+1}")

    new_block_lines = [
        '    SYSTEM_PROMPT = f"""{base_prompt}',
        '',
        '[当前持有的资产凭证]',
        '一台通过{protocol.upper()}协议纳管的资产：',
        '- 目标IP/主机名: {host}',
        '- 端口: {port}',
        '- 账号: {username}',
        '- 密码/Token: {password}',
        '{extra_creds_str}',
        "{'⚠️ 注意：这是一个虚拟会话，请不要使用 `linux_execute_command`，应使用 `local_execute_script` 工具。' if is_virtual else '直接使用 `linux_execute_command` 执行 bash 命令。'}",
        '',
        '[上级指挥官委派的任务]',
        '你是第一线的运维管理工程师调用的 Agent。',
        '上级委派给你的任务是：',
        '{task_description}',
        '',
        '请在当前的会话（{host}）内，利用你的技能和工具，全力完成该任务。',
        '在完成操作、修复或检查完成后，给出一份详细的「执行结果报告」。该报告将直接返回给上级指挥官作为你的工作内容。',
        '"""',
    ]

    lines[block_start:block_end+1] = new_block_lines
    print("Replaced second SYSTEM_PROMPT block")
else:
    print("ERROR: Could not find second SYSTEM_PROMPT block")

content = '\n'.join(lines)

# Fix the user content mojibake
old_user = '{"role": "user", "content": "\u04bf\u043a\u0455\u043c\u0418\u04b3"}'
new_user = '{"role": "user", "content": "\u8bf7\u5f00\u59cb\u6267\u884c\u4efb\u52a1\u3002"}'
if old_user in content:
    content = content.replace(old_user, new_user)
    print("Fixed user content mojibake")
else:
    # Try to find and fix it by looking at the raw chars
    for i, line in enumerate(content.split('\n')):
        if '"content":' in line and '"role": "user"' in content.split('\n')[i-1] if i > 0 else False:
            pass
    # Try broader match
    import re
    pattern = r'\{"role": "user", "content": "[^"]*"\}'
    matches = list(re.finditer(pattern, content))
    for m in matches:
        text = m.group()
        # Check if it has mojibake chars
        if any(ord(c) > 0x400 for c in text) and 'user_message' not in text:
            content = content[:m.start()] + '{"role": "user", "content": "请开始执行任务。"}' + content[m.end():]
            print(f"Fixed user content via regex at pos {m.start()}")
            break

# Remove duplicate import asyncio inside loop
content = content.replace(
    '                import asyncio\n                tool_res = await dispatcher.route_and_execute',
    '                tool_res = await dispatcher.route_and_execute'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Second pass fix complete")
