import re

with open('api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we don't have duplicated ProviderConfig classes
content = re.sub(r'class ProviderConfig\(BaseModel\):[\s\S]*?models: str', '''class ProviderConfig(BaseModel):
    id: str
    name: str
    protocol: str
    base_url: str
    api_key: str
    models: str''', content)

with open('api/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
