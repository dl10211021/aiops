import re
import os

with open('core/llm_factory.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure get_client_for_model strips slashes or handles timeouts better?
# Actually the test passed perfectly locally.

# Let's ensure the fallback works
new_content = re.sub(
    r'api_key = provider\.get\("api_key", "dummy"\)\n    if not api_key:\n        api_key = "dummy"',
    '''api_key = provider.get("api_key", "dummy")
    if not api_key:
        api_key = "dummy"''',
    content
)

with open('core/llm_factory.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
