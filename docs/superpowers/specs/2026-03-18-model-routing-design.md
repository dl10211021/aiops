# Model Routing and Configuration Design

## Objective
Implement a multi-provider, multi-protocol model routing system similar to `opencode`. This allows users to select different models during a session, and the system dynamically routes the request to the correct provider (OpenAI, Anthropic, Google, local models like Ollama/vLLM) using the appropriate protocol. It will also support configurable "thinking modes" (low, medium, high, off) for reasoning models.

## Architecture

1.  **Configuration Management (`models.json`)**:
    *   A central JSON file at the project root (`models.json`) will store all available model configurations.
    *   Each entry will define the model ID, provider, protocol (e.g., `openai`, `anthropic`), base URL, environment variable for the API key, and specific capability flags (like `supports_thinking`).
    *   This naturally supports local providers (Ollama, vLLM) by simply setting `provider: "local"` and pointing `base_url` to the local endpoint (e.g., `http://localhost:11434/v1`).

2.  **Client Factory (`core/llm_factory.py`)**:
    *   A new module responsible for instantiating the correct asynchronous client based on the requested `model_name`.
    *   When a request comes in for `model_name="claude-3-7-sonnet"`, the factory checks the config, uses the `anthropic` protocol, fetches the API key, and returns an `AsyncAnthropic` client instance.
    *   If a model uses the `openai` protocol (including Qwen, Google, Ollama, vLLM), it returns an `AsyncOpenAI` client pointing to the specific `base_url`.

3.  **Unified Execution Layer (`core/llm_execution.py`)**:
    *   Provides a unified wrapper `execute_chat_stream(model_name, messages, thinking_mode)`.
    *   **Thinking Mode Implementation**: 
        *   Accepts `thinking_mode` ("off", "low", "medium", "high").
        *   For Anthropic (Claude 3.7): translates this to specific `budget_tokens` if enabled.
        *   For OpenAI-compatible reasoning models (like `o1`, `o3-mini`, `deepseek-r1`): maps to `reasoning_effort` ("low", "medium", "high").
        *   If the model configuration says `supports_thinking: false`, it ignores the thinking mode.
    *   Translates the standard message format into the provider's required format.
    *   Yields streaming chunks uniformly back to `chat_stream_agent`.

## Components

### `models.json` (Example Structure)

```json
{
  "default_model": "gemini-2.5-flash",
  "models": {
    "gemini-2.5-flash": {
      "provider": "google",
      "protocol": "openai",
      "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
      "api_key_env": "GOOGLE_API_KEY",
      "supports_thinking": false
    },
    "claude-3-7-sonnet-20250219": {
      "provider": "anthropic",
      "protocol": "anthropic",
      "api_key_env": "ANTHROPIC_API_KEY",
      "supports_thinking": true
    },
    "o3-mini": {
      "provider": "openai",
      "protocol": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY",
      "supports_thinking": true
    },
    "ollama-deepseek-r1": {
      "provider": "local",
      "protocol": "openai",
      "base_url": "http://localhost:11434/v1",
      "api_key_env": "",
      "supports_thinking": true
    },
    "vllm-llama3": {
      "provider": "local",
      "protocol": "openai",
      "base_url": "http://localhost:8000/v1",
      "api_key_env": "",
      "supports_thinking": false
    }
  }
}
```

### Changes Required

1.  **Create `models.json`**: Add configurations for Google, Anthropic, OpenAI, Ollama, and vLLM.
2.  **Create `core/llm_factory.py`**: Implement configuration loading and client instantiation.
3.  **Create `core/llm_execution.py`**: 
    *   Implement adapter logic (`format_messages`, `extract_chunk`).
    *   Implement **Thinking Mode Logic**: map "low/medium/high" to `reasoning_effort` (OpenAI style) or `thinking: {"type": "enabled", "budget_tokens": ...}` (Anthropic style).
4.  **Refactor `core/agent.py`**:
    *   Remove global `client`.
    *   Update `chat_stream_agent` to accept `thinking_mode` parameter.
    *   Call `llm_execution.execute_chat_stream` instead of calling `client` directly.
5.  **Refactor `api/routes.py`**:
    *   Update chat endpoints to accept and parse a `thinking_mode` field from the frontend.
    *   Update `get_available_models` to serve the list from `models.json`.

