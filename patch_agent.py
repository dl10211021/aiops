import re

with open('core/agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix syntax error if any
# The patch earlier had a small bug: `grouped_models` logic

new_agent = """
async def get_available_models() -> list:
    try:
        from core.llm_factory import get_all_providers
        from openai import AsyncOpenAI
        import asyncio
        import logging
        
        providers = get_all_providers()
        
        async def fetch_provider_models(p):
            models_list = []
            manual_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            
            if manual_models:
                for m in manual_models:
                    models_list.append({"id": f"{p['id']}|{m}", "name": m})
            elif p.get("protocol") == "openai" and p.get("base_url"):
                try:
                    api_key = p.get("api_key")
                    if not api_key:
                        api_key = "dummy"
                    temp_client = AsyncOpenAI(api_key=api_key, base_url=p.get("base_url"), timeout=5.0)
                    response = await temp_client.models.list()
                    for m in response.data:
                        models_list.append({"id": f"{p['id']}|{m.id}", "name": m.id})
                except Exception as e:
                    pass
            
            if models_list:
                return {"provider_id": p["id"], "provider_name": p["name"], "models": models_list}
            return None

        results = await asyncio.gather(*(fetch_provider_models(p) for p in providers))
        
        grouped_models = [res for res in results if res is not None]
        return grouped_models
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch models: {e}")
        return []
"""

content = re.sub(r'async def get_available_models\(\) -> list:[\s\S]*?return \[\]', new_agent.strip(), content)

with open('core/agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

