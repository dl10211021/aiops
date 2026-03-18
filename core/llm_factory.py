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
    
    # EXPLICITLY PREVENT ENVIRONMENT VARIABLE LEAKS FROM OLD .env CONFIG
    if base_url:
        client_kwargs["base_url"] = base_url
    elif protocol == "openai":
        client_kwargs["base_url"] = "https://api.openai.com/v1"
    elif protocol == "anthropic":
        client_kwargs["base_url"] = "https://api.anthropic.com/v1/"

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
