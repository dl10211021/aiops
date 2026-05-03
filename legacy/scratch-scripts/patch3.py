import re

fpath = "core/agent.py"
with open(fpath, "r", encoding="utf-8") as f:
    c = f.read()

replacement = """if cancel_flags.get(session_id) is True:
                cancel_flags[session_id] = False
                yield f"data: {json.dumps({'type': 'error', 'content': '任务已被手动中止。'})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                break"""

c = re.sub(r'if cancel_flags\.get\(session_id, False\):[\s\S]*?break', replacement, c, count=1)

with open(fpath, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched agent.py")