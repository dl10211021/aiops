from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSISTANT_MODEL_CONFIG_PATH = PROJECT_ROOT / "assistant_model.json"

DEFAULT_ASSISTANT_MODEL_CONFIG: dict[str, Any] = {
    "main_model_id": "",
    "enabled": False,
    "model_id": "",
    "thinking_mode": "high",
    "tasks": {
        "memory_compression": True,
        "trace_review": True,
        "risk_advice": True,
        "asset_profile_prompt": True,
        "completion_check": False,
    },
}


def get_assistant_model_config() -> dict[str, Any]:
    if not ASSISTANT_MODEL_CONFIG_PATH.exists():
        return dict(DEFAULT_ASSISTANT_MODEL_CONFIG)
    try:
        with open(ASSISTANT_MODEL_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_assistant_model_config(data)
    except Exception:
        return dict(DEFAULT_ASSISTANT_MODEL_CONFIG)


def save_assistant_model_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_assistant_model_config(config)
    ASSISTANT_MODEL_CONFIG_PATH.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return normalized


def normalize_assistant_model_config(config: dict[str, Any]) -> dict[str, Any]:
    item = dict(DEFAULT_ASSISTANT_MODEL_CONFIG)
    incoming = dict(config or {})
    tasks = dict(item["tasks"])
    tasks.update(incoming.get("tasks") if isinstance(incoming.get("tasks"), dict) else {})
    item.update(
        {
            "main_model_id": str(incoming.get("main_model_id") or "").strip(),
            "enabled": bool(incoming.get("enabled")),
            "model_id": str(incoming.get("model_id") or "").strip(),
            "thinking_mode": str(incoming.get("thinking_mode") or "high").strip() or "high",
            "tasks": {key: bool(value) for key, value in tasks.items()},
        }
    )
    if item["thinking_mode"] not in {"off", "low", "medium", "high", "enabled"}:
        item["thinking_mode"] = "high"
    return item


def resolve_assistant_model_id(fallback_model_id: str | None = None) -> str:
    config = get_assistant_model_config()
    if config.get("enabled") and config.get("model_id"):
        return str(config["model_id"])
    if fallback_model_id:
        return fallback_model_id
    from core.llm_factory import get_default_model_id

    return get_default_model_id()


def configured_main_model_id() -> str:
    return str(get_assistant_model_config().get("main_model_id") or "").strip()


def resolve_main_model_id(fallback_model_id: str | None = None) -> str:
    configured = configured_main_model_id()
    if configured:
        return configured
    if fallback_model_id:
        return fallback_model_id
    from core.llm_factory import get_default_model_id

    return get_default_model_id()


def assistant_thinking_mode() -> str:
    return str(get_assistant_model_config().get("thinking_mode") or "high")


def assistant_task_enabled(task: str) -> bool:
    config = get_assistant_model_config()
    tasks = config.get("tasks") if isinstance(config.get("tasks"), dict) else {}
    return bool(tasks.get(task, True))
