"""Fix mojibake and encoding issues in core/agent.py"""
import sys

filepath = r"D:\AI\skillops - 20260225\core\agent.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# === Fix 1: Replace first SYSTEM_PROMPT block (chat_stream_agent) ===
first_block_start = None
first_block_end = None
for i, line in enumerate(lines):
    if i >= 76 and i <= 82 and 'extra_creds_str' in line and 'join' in line:
        first_block_start = i - 1  # comment line before it
        break

if first_block_start is None:
    print("ERROR: Could not find first extra_creds_str block")
    sys.exit(1)

# Find the closing triple-quote of first SYSTEM_PROMPT
for i in range(first_block_start + 3, len(lines)):
    stripped = lines[i].strip()
    if stripped == '"""' and i > first_block_start + 10:
        first_block_end = i
        break

print(f"First SYSTEM_PROMPT block: lines {first_block_start+1} to {first_block_end+1}")

new_first_block = '''    # 凭证信息格式化为字符串
    extra_creds_str = "\\\\n".join([f"- {k}: {v}" for k, v in extra_args.items() if v])

    SYSTEM_PROMPT = f"""
{base_prompt}

[当前持有的资产凭证]
一台通过{protocol.upper()}协议纳管的资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 密码/Token: {password}
{extra_creds_str}
{'⚠️ 注意：这是一个虚拟会话，请不要使用 `linux_execute_command`。你应该使用 `local_execute_script` 工具去执行本地的 Python 脚本来获取数据。' if is_virtual else '直接使用 `linux_execute_command` 执行 bash 命令。'}

[已知安全模式]
1. 用户动态加载的「可用Skills」决定了你「什么时候能调什么路」。仔细阅读已加载的技能说明！
2. 当前会话权限状态：{'**高级读写修改权限**：可以执行修改系统的操作' if allow_modifications else '**只读安全模式**：禁止修改系统的文件。除非用户强制要求，否则请确认后拒绝'}
3. 执行某些较高风险脚本时，请仔细参考技能说明中提供的 `<SKILL_ABSOLUTE_PATH>` 路径和 `cwd` 工作目录路径。不要自己凭空猜测目录

[AIOps 专家行为准则 (CRITICAL)]
作为运维管理工程师现场助手级别的专业伙伴：
- **主动规划 (Proactive Planning)**：在接到运维操作任务时，明确列出操作思路和步骤 (Step 1, Step 2...)，不要盲目执行指令
- **根因分析 (Root Cause Analysis)**：不要肤浅地只看表面。要像一名工程师一样，一步一步深入地直接指向异常
- **闭环思维 (Closed-loop)**：操作、修复后自动执行修复验证确认修复
- **心跳巡检 (Heartbeat)**：在「系统空闲」时期，主动执行系统的健康指标全面巡检（包括 CPU、内存、磁盘、关键服务状态），在发现异常时主动通报
- **自我进化与未知资产应对 (Self-Evolution)**：当用户要你「安装」「修复」「改」或「打一个新技能」时，不要说「没有权限」。使用 `evolve_skill` 去修复或变更你的代码。更重要的是：**面对未知类型的设备（安全设备、数据库等），发现当前技能不匹配时，不要放弃！应使用 `local_execute_script` 动态生成并在本地执行 Python 脚本**（如 requests、pymysql 等），探测目标设备。一旦探测成功，使用 `evolve_skill` 将探测过程固化为一个新的「可复用技能」

[使用的基础执行工具]
- linux_execute_command: 在远程的目标 Linux 机器上执行 bash 命令 (需要 SSH 资产)
- local_execute_script: 在本地执行 Python 或 Shell 脚本 (所有资产类型均可执行)

[当前已加载专业技能说明 (Skills)]
以下是当前专业技能的详细 <INSTRUCTIONS> 指令，请严格遵照其中的步骤进行操作
{dispatcher.get_skill_instructions(active_skills)}

{ltm_context}
"""
'''

lines[first_block_start:first_block_end+1] = [new_first_block]

# === Fix 2: Replace second SYSTEM_PROMPT block (headless_agent_chat) ===
second_block_start = None
second_block_end = None
for i, line in enumerate(lines):
    if i >= 230 and 'extra_creds_str' in line and 'join' in line:
        second_block_start = i
        break

if second_block_start:
    for i in range(second_block_start + 3, len(lines)):
        stripped = lines[i].strip()
        if stripped == '"""' and i > second_block_start + 5:
            second_block_end = i
            break

    print(f"Second SYSTEM_PROMPT block: lines {second_block_start+1} to {second_block_end+1}")

    new_second_block = '''    extra_creds_str = "\\\\n".join([f"- {k}: {v}" for k, v in extra_args.items() if v])

    SYSTEM_PROMPT = f"""{base_prompt}

[当前持有的资产凭证]
一台通过{protocol.upper()}协议纳管的资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 密码/Token: {password}
{extra_creds_str}
{'⚠️ 注意：这是一个虚拟会话，请不要使用 `linux_execute_command`，应使用 `local_execute_script` 工具。' if is_virtual else '直接使用 `linux_execute_command` 执行 bash 命令。'}

[上级指挥官委派的任务]
你是第一线的运维管理工程师调用的 Agent。
上级委派给你的任务是：
{task_description}

请在当前的会话（{host}）内，利用你的技能和工具，全力完成该任务。
在完成操作、修复或检查完成后，给出一份详细的「执行结果报告」。该报告将直接返回给上级指挥官作为你的工作内容。
"""
'''
    lines[second_block_start:second_block_end+1] = [new_second_block]

# Join back and do string-level fixes
content = ''.join(lines)

# Fix remaining mojibake in inline strings - use line-by-line approach
new_lines = []
for line in content.split('\n'):
    # Fix headless docstring
    if '"""' in line and 'Agent' in line and len(line) > 50 and 'headless' not in line.lower() and 'def' not in line:
        if any(ord(c) > 0x300 and ord(c) < 0x500 for c in line):
            line = '    """后台无头模式的 Agent 循环，用于协同任务的结果汇报。"""'

    # Fix session not found return
    if 'return f"' in line and '{session_id}' in line and any(ord(c) > 0x300 for c in line):
        line = '        return f"目标会话 {session_id} 不在线或已过期。"'

    # Fix fallback base_prompt in headless
    if 'base_prompt = "' in line and 'OpsCore' in line and any(ord(c) > 0x300 for c in line):
        line = '        base_prompt = "你是 OpsCore 的高级 AI 运维专家。"'

    # Fix user content in headless messages
    if '"content":' in line and '"user"' not in line and any(ord(c) > 0x400 for c in line) and 'role' not in line:
        if 'user' in str(new_lines[-1:]):
            line = '        {"role": "user", "content": "请开始执行任务。"}'

    # Fix success return in headless
    if 'return f"' in line and 'agent_profile' in line and 'Agent' in line and any(ord(c) > 0x300 for c in line):
        line = '        return f"来自 {agent_profile} Agent ({host}) 的协同任务报告：\\n" + assistant_content'

    # Fix error return in headless
    if 'return f"' in line and '{host}' in line and '{e}"' in line and any(ord(c) > 0x300 for c in line):
        line = '        return f"协同任务执行失败。目标节点 {host} 执行报错: {e}"'

    # Remove duplicate 'import asyncio' inside loop
    if line.strip() == 'import asyncio' and any('for tc in' in l for l in new_lines[-5:]):
        continue

    # Remove duplicate 'import os' in headless (if preceded by headless function context)
    if line.strip() == 'import os' and any('headless' in l or 'profile_path' in l for l in new_lines[-3:]):
        continue

    # Fix mojibake comments
    if line.strip().startswith('#') and any(ord(c) > 0x300 and ord(c) < 0x500 for c in line):
        if 'SQLite' in line:
            line = '    # 从 SQLite 中读取之前的有效会话（去掉之前的 system 提示词）'
        elif 'db' in line.lower() or '\u04dd' in line:
            line = '    # 最新一条用户消息存入数据库'
        elif '50' in line:
            line = '        for iteration in range(50): # 扩展至 50 轮'
        elif 'asyncio' in line.lower() or '\u044c' in line:
            line = '        # 每轮对话结束后，触发异步记忆压缩'

    new_lines.append(line)

content = '\n'.join(new_lines)

# Fix the user message line more precisely
content = content.replace(
    '{"role": "user", "content": "\u04bf\u043a\u0455\u043c\u0418\u04b3"}',
    '{"role": "user", "content": "请开始执行任务。"}'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: agent.py mojibake fixed")
