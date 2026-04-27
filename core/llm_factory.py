import json
import re
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


SUPPORTED_PROVIDER_PROTOCOLS = {"openai", "anthropic", "custom"}
MASKED_SECRET = "********"


def normalize_provider_config(provider: dict) -> dict:
    """Normalize provider config at the API boundary before saving or using it."""
    item = dict(provider or {})
    provider_id = str(item.get("id") or "").strip()
    provider_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", provider_id).strip("._-")
    if not provider_id:
        provider_id = "custom"

    protocol = str(item.get("protocol") or "openai").strip().lower()
    if protocol == "custom":
        protocol = "openai"
    if protocol not in {"openai", "anthropic"}:
        protocol = "openai"

    name = str(item.get("name") or "").strip() or provider_id
    base_url = str(item.get("base_url") or "").strip()
    api_key = str(item.get("api_key") or "").strip()
    models = item.get("models", "")
    if isinstance(models, list):
        models = ",".join(str(m).strip() for m in models if str(m).strip())
    else:
        models = str(models or "").strip()

    return {
        "id": provider_id,
        "name": name,
        "protocol": protocol,
        "base_url": base_url,
        "api_key": api_key,
        "models": models,
    }


def normalize_providers(providers: list[dict]) -> list[dict]:
    seen = set()
    normalized = []
    for provider in providers or []:
        item = normalize_provider_config(provider)
        base_id = item["id"]
        suffix = 2
        while item["id"] in seen:
            item["id"] = f"{base_id}_{suffix}"
            suffix += 1
        seen.add(item["id"])
        normalized.append(item)
    return normalized


def mask_provider_secrets(providers):
    masked = []
    for provider in normalize_providers(providers):
        item = dict(provider)
        if item.get("api_key"):
            item["api_key"] = MASKED_SECRET
        masked.append(item)
    return masked


def merge_provider_secrets(incoming, existing):
    existing_by_id = {p.get("id"): p for p in normalize_providers(existing)}
    merged = []
    for provider in incoming:
        item = normalize_provider_config(provider)
        old = existing_by_id.get(item.get("id"), {})
        if item.get("api_key") == MASKED_SECRET:
            item["api_key"] = old.get("api_key", "")
        merged.append(item)
    return merged

def get_all_providers():
    if not PROVIDERS_JSON_PATH.exists():
        save_providers(DEFAULT_PROVIDERS)
        return normalize_providers(DEFAULT_PROVIDERS)
    try:
        with open(PROVIDERS_JSON_PATH, "r", encoding="utf-8") as f:
            return normalize_providers(json.load(f))
    except Exception:
        return normalize_providers(DEFAULT_PROVIDERS)

def save_providers(providers):
    normalized = normalize_providers(providers)
    PROVIDERS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = PROVIDERS_JSON_PATH.with_suffix(PROVIDERS_JSON_PATH.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(PROVIDERS_JSON_PATH)

def get_default_model_id() -> str:
    """Return the first configured model as a provider-qualified id."""
    providers = get_all_providers()
    for provider in providers:
        models = [m.strip() for m in provider.get("models", "").split(",") if m.strip()]
        if models:
            return f"{provider['id']}|{models[0]}"
    if providers:
        return f"{providers[0]['id']}|none"
    raise ValueError("No model provider is configured")

def get_embedding_client_and_model(full_model_id: str | None = None):
    """Resolve the embedding client/model without falling back to hard-coded Gemini."""
    import os

    model_id = os.environ.get("EMBEDDING_MODEL_ID") or full_model_id or get_default_model_id()
    client, config = get_client_for_model(model_id)
    embedding_model = os.environ.get("EMBEDDING_MODEL") or config["model"]
    return client, embedding_model

def get_client_for_model(full_model_id: str):
    if not full_model_id:
        full_model_id = get_default_model_id()
    providers = get_all_providers()
    
    provider_id = None
    model_name = full_model_id
    
    if "|" in full_model_id:
        provider_id, model_name = full_model_id.split("|", 1)
        
    provider = None
    if provider_id:
        provider = next((p for p in providers if p.get("id") == provider_id), None)

    if not provider:
        # Fallback: try to find the model in the manual lists
        for p in providers:
            p_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            if model_name in p_models:
                provider = p
                break
        if not provider and providers:
            provider = providers[0] # ultimate fallback

    if not provider:        raise ValueError(f"No suitable provider found for model '{full_model_id}'")
        
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
