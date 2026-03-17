import codecs
import re

fpath = "core/agent.py"
with codecs.open(fpath, "r", "utf-8", errors="ignore") as f:
    c = f.read()

def repl(m):
    indent = m.group(1)
    original = m.group(0)
    check = indent + "    if cancel_flags.get(session_id, False):\\n"
    check += indent + "        yield f\"data: {json.dumps({'type': 'error', 'content': '任务已被手动中止。'})}\\\\n\\\\n\"\\n"
    check += indent + "        yield f\"data: {json.dumps({'type': 'done'})}\\\\n\\\\n\"\\n"
    check += indent + "        break\\n"
    # Actually just use triple quotes to avoid escape hell
    return original + "\n" + indent + "    if cancel_flags.get(session_id, False):\n" + indent + "        yield f\"data: {json.dumps({'type': 'error', 'content': '任务已被手动中止。'})}\\n\\n\"\n" + indent + "        yield f\"data: {json.dumps({'type': 'done'})}\\n\\n\"\n" + indent + "        break\n"

c = re.sub(r'^(\s+)for iteration in range\(50\):.*$', repl, c, flags=re.MULTILINE, count=1)

with codecs.open(fpath, "w", "utf-8") as f:
    f.write(c)

print("Agent patched.")