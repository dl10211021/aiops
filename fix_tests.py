import re

with open('tests/test_llm_factory.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make the tests compatible with our new provider mechanism
content = content.replace('def setUp(self):', '''def setUp(self):
        from core.llm_factory import DEFAULT_PROVIDERS, save_providers
        save_providers(DEFAULT_PROVIDERS)
        import os''')
        
with open('tests/test_llm_factory.py', 'w', encoding='utf-8') as f:
    f.write(content)
