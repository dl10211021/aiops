import codecs
import re

fpath = "core/agent.py"
with codecs.open(fpath, "r", "utf-8") as f:
    c = f.read()

# 1. Add cancel_flags near the top
if "cancel_flags = {}" not in c:
    c = c.replace("from core.dispatcher import dispatcher
", "from core.dispatcher import dispatcher

cancel_flags = {}
")

# 2. Add cancel check in chat_stream_agent
# find exactly `        for iteration in range(50):`
# we only want to replace the first one (in chat_stream_agent)
c = re.sub(
    r'(\s+)for iteration in range\(50\):(.*)', 
    r'\1for iteration in range(50):
\1    if cancel_flags.get(session_id, False):
\1        yield f"data: {json.dumps({'type': 'error', 'content': '🛑 任务已被用户手动终止。'})}

"
\1        yield f"data: {json.dumps({'type': 'done'})}

"
\1        break', 
    c, 
    count=1
)

with codecs.open(fpath, "w", "utf-8") as f:
    f.write(c)

print("Agent patched.")