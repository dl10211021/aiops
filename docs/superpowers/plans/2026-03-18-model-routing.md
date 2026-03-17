# Model Routing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified multi-provider model routing system (OpenAI, Anthropic, Google, local Ollama/vLLM) with thinking mode support.

**Architecture:** Create a `models.json` config, a `core/llm_factory.py` to instantiate `AsyncOpenAI` or `AsyncAnthropic` clients, and a `core/llm_execution.py` to adapt messages, handle thinking parameters, and stream responses back to `chat_stream_agent`.

**Tech Stack:** Python, FastAPI, AsyncOpenAI, AsyncAnthropic, Pydantic

---

### Task 1: Create Global Configuration

**Files:**
- Create: `models.json`
- Modify: `api/routes.py`
- Modify: `core/agent.py`

- [ ] **Step 1: Create `models.json` file**
Create the `models.json` file in the root directory with the structure defined in the design document (including Google, Anthropic, OpenAI, Ollama, and vLLM).

- [ ] **Step 2: Update `api/routes.py` to serve models from JSON**
Update `get_available_models` endpoint to read from `models.json` instead of querying the API directly.

- [ ] **Step 3: Test configuration loading**
Run a simple script or `pytest` to verify `json.load("models.json")` works and structure is correct.

- [ ] **Step 4: Commit**
`git add models.json api/routes.py`
`git commit -m "feat: add models.json configuration and update API to serve it"`

### Task 2: Implement Client Factory

**Files:**
- Create: `core/llm_factory.py`
- Create: `requirements.txt` (Update)

- [ ] **Step 1: Update requirements**
Ensure `anthropic` is in `requirements.txt` alongside `openai`.

- [ ] **Step 2: Create `core/llm_factory.py`**
Implement `get_client_for_model(model_name: str)` function that reads `models.json`, checks `protocol`, and returns either `AsyncOpenAI` or `AsyncAnthropic` client. Also return the model config dict for later use.

- [ ] **Step 3: Handle environment variables**
Ensure the factory reads the correct API key from `os.getenv(config["api_key_env"])` and raises a clear `ValueError` if missing (unless it's a local provider).

- [ ] **Step 4: Commit**
`git add core/llm_factory.py requirements.txt`
`git commit -m "feat: implement llm_factory for dynamic client instantiation"`

### Task 3: Implement Execution Layer & Thinking Mode

**Files:**
- Create: `core/llm_execution.py`

- [ ] **Step 1: Create execution wrapper**
Create `execute_chat_stream(model_name: str, messages: list, thinking_mode: str = "off")` in `core/llm_execution.py`.

- [ ] **Step 2: Implement protocol adapters**
Inside the wrapper, handle `protocol == "anthropic"` vs `protocol == "openai"`. 
- For Anthropic: map standard `{"role": "user", "content": "..."}`. Translate `thinking_mode` to `thinking={"type": "enabled", "budget_tokens": X}` if `supports_thinking` is true.
- For OpenAI: handle standard format. Translate `thinking_mode` to `reasoning_effort` for supported models like o1/o3-mini.

- [ ] **Step 3: Unify stream yielding**
Iterate over the specific SDK stream and yield chunks uniformly:
- Anthropic: check for `content_block_delta` and `text` or `thinking` blocks.
- OpenAI: check for `chunk.choices[0].delta.content` or `reasoning_content`.

- [ ] **Step 4: Commit**
`git add core/llm_execution.py`
`git commit -m "feat: implement unified llm execution layer with thinking mode"`

### Task 4: Integrate with Core Agent & API

**Files:**
- Modify: `core/agent.py`
- Modify: `api/routes.py`

- [ ] **Step 1: Refactor `chat_stream_agent`**
In `core/agent.py`, remove the global `client`. Update `chat_stream_agent` signature to accept `thinking_mode: str = "off"`. Call `execute_chat_stream` from `llm_execution` instead of the old client.

- [ ] **Step 2: Refactor API Chat Endpoints**
In `api/routes.py`, update `ChatRequest` to include `thinking_mode: Optional[str] = "off"`. Pass this to `chat_stream_agent`.

- [ ] **Step 3: Cleanup deprecated config**
Remove or modify `update_client_config` and the `/config/llm` POST endpoint since config is now file-based.

- [ ] **Step 4: Commit**
`git add core/agent.py api/routes.py`
`git commit -m "refactor: integrate new model routing into agent and API"`

