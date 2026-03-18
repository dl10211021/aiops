import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace port=9000 with port=8000
content = content.replace('port=9000', 'port=8000')
content = content.replace('http://localhost:9000', 'http://localhost:8000')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('frontend/vite.config.ts', 'r', encoding='utf-8') as f:
    vite_content = f.read()

vite_content = vite_content.replace('http://localhost:9000', 'http://localhost:8000')

with open('frontend/vite.config.ts', 'w', encoding='utf-8') as f:
    f.write(vite_content)
