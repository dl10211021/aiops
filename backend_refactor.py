import os
import json
import re

# 1. Update .gitignore to ignore providers.json
gitignore_path = '.gitignore'
if os.path.exists(gitignore_path):
    with open(gitignore_path, 'r') as f:
        content = f.read()
    if 'providers.json' not in content:
        with open(gitignore_path, 'a') as f:
            f.write('\nproviders.json\n')

# 2. Create default providers.json logic in llm_factory
factory_code = '''
import os
import json
import uuid
from pathlib import Path
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_JSON_PATH = PROJECT_ROOT / "providers.json"

DEFAULT_PROVIDERS = [
    {
        "id": "google",
        "name": "Google Gemini",
        "protocol": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "",
        "models": "gemini-2.5-flash,gemini-2.5-pro,gemini-2.0-flash-thinking-exp"
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "protocol": "anthropic",
        "base_url": "https://api.anthropic.com/v1/",
        "api_key": "",
        "models": "claude-3-7-sonnet-20250219,claude-3-5-sonnet-20241022"
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "protocol": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "models": "deepseek-chat,deepseek-reasoner"
    },
    {
        "id": "ollama",
        "name": "Ollama (本地)",
        "protocol": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key": "dummy",
        "models": ""
    }
]

def get_all_providers():
    if not PROVIDERS_JSON_PATH.exists():
        with open(PROVIDERS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROVIDERS, f, ensure_ascii=False, indent=2)
        return DEFAULT_PROVIDERS
    try:
        with open(PROVIDERS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROVIDERS

def save_providers(providers):
    with open(PROVIDERS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(providers, f, ensure_ascii=False, indent=2)

def get_client_for_model(full_model_id: str):
    providers = get_all_providers()
    
    provider_id = None
    model_name = full_model_id
    
    if "|" in full_model_id:
        provider_id, model_name = full_model_id.split("|", 1)
        
    provider = None
    if provider_id:
        provider = next((p for p in providers if p.get("id") == provider_id), None)
    else:
        # Fallback: try to find the model in the manual lists
        for p in providers:
            p_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            if model_name in p_models:
                provider = p
                break
        if not provider and providers:
            provider = providers[0] # ultimate fallback
            
    if not provider:
        raise ValueError(f"No suitable provider found for model '{full_model_id}'")
        
    protocol = provider.get("protocol", "openai")
    api_key = provider.get("api_key", "dummy")
    if not api_key:
        api_key = "dummy"
    base_url = provider.get("base_url")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    if protocol == "openai":
        client = AsyncOpenAI(**client_kwargs)
    elif protocol == "anthropic":
        client = AsyncAnthropic(**client_kwargs)
    else:
        raise ValueError(f"Unsupported protocol '{protocol}'")

    config = {
        "protocol": protocol,
        "model": model_name,
        "supports_thinking": "reasoner" in model_name or "thinking" in model_name or "claude-3-7" in model_name or "o3-" in model_name or "o1-" in model_name or "r1" in model_name.lower()
    }
    return client, config
'''
with open('core/llm_factory.py', 'w', encoding='utf-8') as f:
    f.write(factory_code.strip() + '\n')

# 3. Update agent.py get_available_models
agent_patch = '''
async def get_available_models() -> list:
    try:
        from core.llm_factory import get_all_providers
        from openai import AsyncOpenAI
        import asyncio
        
        providers = get_all_providers()
        grouped_models = []
        
        async def fetch_provider_models(p):
            models_list = []
            manual_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            
            if manual_models:
                # If user manually defined models, use them
                for m in manual_models:
                    models_list.append({"id": f"{p['id']}|{m}", "name": m})
            else:
                # Dynamic fetch if empty and protocol is openai
                if p.get("protocol") == "openai" and p.get("base_url"):
                    try:
                        temp_client = AsyncOpenAI(api_key=p.get("api_key", "dummy"), base_url=p.get("base_url"), timeout=5.0)
                        response = await temp_client.models.list()
                        for m in response.data:
                            models_list.append({"id": f"{p['id']}|{m.id}", "name": m.id})
                    except Exception as e:
                        pass
            
            if models_list:
                return {"provider_id": p["id"], "provider_name": p["name"], "models": models_list}
            return None

        results = await asyncio.gather(*(fetch_provider_models(p) for p in providers))
        for res in results:
            if res:
                grouped_models.append(res)
                
        return grouped_models
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch models: {e}")
        return []
'''

with open('core/agent.py', 'r', encoding='utf-8') as f:
    agent_content = f.read()
import re
agent_content = re.sub(r'async def get_available_models\(\) -> list:[\s\S]*?return \[\]', agent_patch.strip(), agent_content)
with open('core/agent.py', 'w', encoding='utf-8') as f:
    f.write(agent_content)

# 4. Update routes.py
routes_patch_1 = '''
from typing import List

class ProviderConfig(BaseModel):
    id: str
    name: str
    protocol: str
    base_url: str
    api_key: str
    models: str
'''

with open('api/routes.py', 'r', encoding='utf-8') as f:
    routes_content = f.read()

# remove old LLMConfig things if they exist
routes_content = re.sub(r'class LLMConfigRequest\(BaseModel\):[\s\S]*?class EmbeddingConfigRequest', 'class EmbeddingConfigRequest', routes_content)
routes_content = re.sub(r'@router\.get\("/config/llm"[\s\S]*?@router\.post\("/config/llm"[\s\S]*?except Exception as e:\s*raise HTTPException\(status_code=500, detail=str\(e\)\)', '', routes_content)

# add the new ones
routes_patch_2 = '''
@router.get("/config/providers", response_model=ResponseModel)
async def get_providers_endpoint():
    from core.llm_factory import get_all_providers
    providers = get_all_providers()
    return ResponseModel(status="success", data={"providers": providers})

@router.post("/config/providers", response_model=ResponseModel)
async def update_providers_endpoint(req: List[ProviderConfig]):
    from core.llm_factory import save_providers
    providers_dict = [p.model_dump() for p in req]
    save_providers(providers_dict)
    return ResponseModel(status="success", message="供应商配置已保存")
'''

routes_content = routes_content.replace('class EmbeddingConfigRequest(BaseModel):', routes_patch_1 + '\nclass EmbeddingConfigRequest(BaseModel):')
routes_content += '\n' + routes_patch_2 + '\n'

with open('api/routes.py', 'w', encoding='utf-8') as f:
    f.write(routes_content)

