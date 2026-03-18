import re

with open('core/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make the timeout even shorter so if an endpoint like Google hangs, the whole fetch doesn't hang.
# Also fix the fallback issue where it could take up to 20 seconds per endpoint.
content = content.replace('timeout=20.0', 'timeout=3.0')

with open('core/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
