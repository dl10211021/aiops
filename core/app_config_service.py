from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from core.agent import (
    get_embedding_config,
    update_embedding_config,
)
from core.agent_runtime_config import (
    get_agent_runtime_config,
    update_agent_runtime_config,
)


logger = logging.getLogger(__name__)
ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class AppConfigServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def read_env_file_values(env_path: Path = ENV_FILE_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def update_env_file_values(values: dict[str, str], env_path: Path = ENV_FILE_PATH) -> None:
    env_lines: list[str] = []
    if env_path.exists():
        env_lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)

    keys = set(values)
    filtered = [
        line
        for line in env_lines
        if not any(line.startswith(f"{key}=") for key in keys)
    ]
    for key, value in values.items():
        filtered.append(f"{key}={value}\n")
    env_path.write_text("".join(filtered), encoding="utf-8")


def build_llm_config_payload(
    env: Mapping[str, str] | None = None,
    env_path: Path = ENV_FILE_PATH,
) -> dict[str, str]:
    runtime_env = env or os.environ
    file_values = read_env_file_values(env_path)
    base_url = runtime_env.get("OPENAI_BASE_URL") or file_values.get("OPENAI_BASE_URL") or DEFAULT_LLM_BASE_URL
    api_key = runtime_env.get("OPENAI_API_KEY") or file_values.get("OPENAI_API_KEY") or ""
    return {
        "base_url": base_url,
        "api_key": "********" if api_key else "",
    }


def get_agent_runtime_config_record() -> dict[str, Any]:
    return get_agent_runtime_config()


def save_agent_runtime_config_record(
    chat_max_steps: int,
    headless_max_steps: int,
    env_path: Path = ENV_FILE_PATH,
) -> dict[str, Any]:
    try:
        config = update_agent_runtime_config(chat_max_steps, headless_max_steps)
        update_env_file_values(
            {
                "OPSCORE_AGENT_MAX_STEPS": str(config["chat_max_steps"]),
                "OPSCORE_HEADLESS_AGENT_MAX_STEPS": str(config["headless_max_steps"]),
            },
            env_path,
        )
        return config
    except Exception as exc:
        logger.error("保存 Agent 执行保护配置失败: %s", exc)
        raise AppConfigServiceError(500, f"保存 Agent 执行保护配置失败: {exc}") from exc


def get_embedding_config_record() -> dict[str, Any]:
    model, dim = get_embedding_config()
    return {"model": model, "dim": dim}


def save_embedding_config_record(
    model: str,
    dim: int,
    env_path: Path = ENV_FILE_PATH,
) -> None:
    try:
        update_embedding_config(model, dim)
        update_env_file_values(
            {
                "EMBEDDING_MODEL": model,
                "EMBEDDING_DIM": str(dim),
            },
            env_path,
        )
        logger.info("Embedding config updated via API: model=%s, dim=%s", model, dim)
    except Exception as exc:
        raise AppConfigServiceError(500, str(exc)) from exc
