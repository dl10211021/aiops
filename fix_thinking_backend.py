import re

with open('core/llm_execution.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure "off" correctly disables thinking if previously passed
# In the original design "off" just didn't pass the parameter.
# Wait, for Anthropic, thinking_mode == "enabled" ? We don't have that logic, we have "low", "medium", "high"
# We should also support "enabled" with a default budget.

new_code = '''
        if supports_thinking and is_thinking_requested:
            budget_map = {"low": 1024, "medium": 4096, "high": 8000, "enabled": 4096}
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget_map.get(thinking_mode, 4096),
            }
            kwargs["temperature"] = 1.0
'''
content = re.sub(r'if supports_thinking and is_thinking_requested:[\s\S]*?kwargs\["temperature"\] = 1\.0', new_code.strip(), content)

# Check if is_thinking_requested logic covers "enabled"
content = content.replace('is_thinking_requested = thinking_mode in ["low", "medium", "high"]', 'is_thinking_requested = thinking_mode in ["low", "medium", "high", "enabled"]')

with open('core/llm_execution.py', 'w', encoding='utf-8') as f:
    f.write(content)
