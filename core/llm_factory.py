import os
import json
from pathlib import Path
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# Calculate project root from current file path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_JSON_PATH = PROJECT_ROOT / "models.json"


def get_client_for_model(model_name: str):
    """
    Reads models.json, determines the protocol, and returns an initialized
    AsyncOpenAI or AsyncAnthropic client along with the model's configuration dict.

    Args:
        model_name: The name of the model to instantiate the client for.

    Returns:
        tuple: (client, config)
    """
    if not MODELS_JSON_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at {MODELS_JSON_PATH}")

    with open(MODELS_JSON_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    models = config_data.get("models", {})
    if model_name not in models:
        # Fallback to globally configured custom OpenAI endpoint (from frontend UI)
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if not api_key:
            api_key = "dummy"
            
        return AsyncOpenAI(api_key=api_key, base_url=base_url), {"protocol": "openai", "model": model_name, "supports_thinking": False}

    config = models[model_name]
    protocol = config.get("protocol")
    api_key_env = config.get("api_key_env")

    api_key = None
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing API key: Environment variable '{api_key_env}' is not set."
            )
    else:
        # Default to a dummy key for local models that don't specify an env var
        # to prevent validation errors from client libraries.
        api_key = "dummy"

    base_url = config.get("base_url")

    # Initialize client kwargs
    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url

    # Instantiate the correct client based on the protocol
    if protocol == "openai":
        client = AsyncOpenAI(**client_kwargs)
    elif protocol == "anthropic":
        client = AsyncAnthropic(**client_kwargs)
    else:
        raise ValueError(f"Unsupported protocol '{protocol}' for model '{model_name}'.")

    return client, config
