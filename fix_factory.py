import re

with open('core/llm_factory.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make the factory accept missing models.json models, using the default OPENAI_* env vars.
new_code = '''
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
'''

content = re.sub(r'def get_client_for_model\(model_name: str\):[\s\S]*?config = models\[model_name\]', new_code.strip(), content)

with open('core/llm_factory.py', 'w', encoding='utf-8') as f:
    f.write(content)
