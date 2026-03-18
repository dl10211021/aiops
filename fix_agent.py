import re

with open('core/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update get_available_models to also fetch from dynamic global base URL if present
new_code = '''
async def get_available_models() -> list:
    try:
        import json
        import os
        from openai import AsyncOpenAI

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "models.json"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        models = list(config.get("models", {}).keys())
        
        # Check if the user has a custom OpenAI Base URL configured via UI
        base_url = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY", "dummy")
        
        if base_url:
            try:
                temp_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=5.0)
                response = await temp_client.models.list()
                dynamic_models = [m.id for m in response.data]
                models.extend(dynamic_models)
            except Exception as dyn_e:
                logger.warning(f"Failed to fetch dynamic models from {base_url}: {dyn_e}")

        # Remove duplicates and sort
        models = list(set(models))
        models.sort()
        return models
    except Exception as e:
        logger.error(f"Failed to fetch models from models.json: {e}")
        return []
'''

content = re.sub(r'async def get_available_models\(\) -> list:[\s\S]*?return \[\]', new_code.strip(), content)

with open('core/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
