import re

with open('core/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Log exceptions instead of pass
content = content.replace('''except Exception as e:
                    pass''', '''except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to fetch models for {p.get('name')}: {e}")''')

with open('core/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
