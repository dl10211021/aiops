# Model Routing and Configuration Design

## Objective
Implement a multi-provider, multi-protocol model routing system similar to `opencode`. This allows users to select different models during a session, and the system dynamically routes the request to the correct provider (OpenAI, Anthropic, Google, local models) using the appropriate protocol.

## Architecture

1.  **Configuration Management (`models.json`)**:
    *   A central JSON file at the project root (`models.json`) will store all available model configurations.
    *   Each entry will define the model ID, provider, protocol (e.g., `openai`, `anthropic`, `gemini`), base URL, and the environment variable name for the API key.
    *   This makes adding or removing models as simple as editing a JSON file.

2.  **Client Factory (`core/llm_factory.py`)**:
    *   A new module responsible for instantiating the correct asynchronous client based on the requested `model_name`.
    *   It reads `models.json` on startup (or on demand) and caches the configurations.
    *   When a request comes in for `model_name="claude-3-5-sonnet"`, the factory checks the config, sees it uses the `anthropic` protocol, fetches the API key from the environment, and returns an `AsyncAnthropic` client instance.
    *   If a model uses the `openai` protocol (like many compatibility layers for Qwen, DeepSeek, Google, etc.), it returns an `AsyncOpenAI` client pointing to the specific `base_url`.

3.  **Unified Execution Layer (`core/llm_execution.py` or updated `core/agent.py`)**:
    *   Different SDKs have different method signatures (e.g., `client.chat.completions.create` vs `client.messages.create`).
    *   We will introduce a thin wrapper/adapter layer that takes a standard message format (list of dicts with `role` and `content`) and translates it into the specific format required by the chosen protocol.
    *   This layer will handle streaming responses and yield chunks in a unified format back to the `chat_stream_agent`.

## Components

### `models.json` (Example Structure)

```json
{
  "models": {
    "gemini-2.5-flash": {
      "provider": "google",
      "protocol": "openai",
      "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
      "api_key_env": "GOOGLE_API_KEY"
    },
    "claude-3-5-sonnet": {
      "provider": "anthropic",
      "protocol": "anthropic",
      "api_key_env": "ANTHROPIC_API_KEY"
    },
    "gpt-4o": {
      "provider": "openai",
      "protocol": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY"
    },
    "qwen-max": {
      "provider": "aliyun",
      "protocol": "openai",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "DASHSCOPE_API_KEY"
    }
  },
  "default_model": "gemini-2.5-flash"
}
```

### Changes Required

1.  **Create `models.json`**: Initialize with current Google Gemini settings via OpenAI compatibility.
2.  **Create `core/llm_factory.py`**: Implement configuration loading and client instantiation logic.
3.  **Refactor `core/agent.py`**:
    *   Remove the global `client` variable.
    *   Update `chat_stream_agent` to use the factory to get the correct execution adapter based on the `model_name`.
    *   Update `get_available_models` to read from `models.json`.
4.  **Refactor `api/routes.py`**:
    *   Update `/config/llm` endpoints to handle modifying `models.json` if dynamic updating via UI is still desired, or deprecate/change them to reflect the new file-based approach. Currently, they update global state.
5.  **Refactor `core/memory.py` & `core/rag.py`**: Ensure embedding generation also uses the factory if different embedding models/providers are needed, or keep it simple for now if embeddings remain constant.

## Error Handling & Fallbacks
*   If a requested model is not found in `models.json`, fallback to the `default_model` specified in the config.
*   If the API key is missing from the environment for a selected provider, raise a clear error to the user indicating which environment variable needs to be set.

## Testing
*   Unit tests for `llm_factory.py` to ensure correct client types are returned.
*   Integration tests with mock API keys to verify the adapter layer correctly formats requests for both `openai` and `anthropic` protocols.
