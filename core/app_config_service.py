from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from core.embedding_config import (
    get_embedding_config,
    update_embedding_config,
)
from core.agent_runtime_config import (
    get_agent_runtime_config,
    update_agent_runtime_config,
)
from core.session_retention import (
    SessionRetentionPolicy,
    session_retention_interval_seconds,
    session_retention_policy_from_env,
)


logger = logging.getLogger(__name__)
ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
SESSION_RETENTION_ENV_KEYS = {
    "enabled": "OPSCORE_SESSION_RETENTION_ENABLED",
    "raw_result_days": "OPSCORE_RETENTION_RAW_RESULT_DAYS",
    "compressed_history_days": "OPSCORE_RETENTION_COMPRESSED_HISTORY_DAYS",
    "audit_metadata_days": "OPSCORE_RETENTION_AUDIT_METADATA_DAYS",
    "max_result_chars": "OPSCORE_RETENTION_MAX_RESULT_CHARS",
    "preview_chars": "OPSCORE_RETENTION_PREVIEW_CHARS",
}


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


def get_session_retention_config_record(
    env: Mapping[str, str] | None = None,
    env_path: Path = ENV_FILE_PATH,
    *,
    include_preview: bool = False,
) -> dict[str, Any]:
    runtime_env = os.environ if env is None else env
    merged_env = {**read_env_file_values(env_path), **dict(runtime_env)}
    policy = session_retention_policy_from_env(merged_env)
    interval_seconds = session_retention_interval_seconds(merged_env)
    config = {
        **asdict(policy),
        "interval_seconds": interval_seconds,
        "defaults": asdict(SessionRetentionPolicy()),
        "env_keys": SESSION_RETENTION_ENV_KEYS,
    }
    if include_preview:
        config["preview"] = preview_session_retention_policy(policy)
        config["status"] = get_session_retention_status_record(interval_seconds=interval_seconds)
    return config


def save_session_retention_config_record(
    *,
    enabled: bool,
    raw_result_days: int,
    compressed_history_days: int,
    audit_metadata_days: int,
    max_result_chars: int,
    preview_chars: int,
    env_path: Path = ENV_FILE_PATH,
) -> dict[str, Any]:
    policy = SessionRetentionPolicy(
        enabled=enabled,
        raw_result_days=raw_result_days,
        compressed_history_days=compressed_history_days,
        audit_metadata_days=audit_metadata_days,
        max_result_chars=max_result_chars,
        preview_chars=preview_chars,
    )
    try:
        values = {
            SESSION_RETENTION_ENV_KEYS["enabled"]: "true" if policy.enabled else "false",
            SESSION_RETENTION_ENV_KEYS["raw_result_days"]: str(policy.raw_result_days),
            SESSION_RETENTION_ENV_KEYS["compressed_history_days"]: str(policy.compressed_history_days),
            SESSION_RETENTION_ENV_KEYS["audit_metadata_days"]: str(policy.audit_metadata_days),
            SESSION_RETENTION_ENV_KEYS["max_result_chars"]: str(policy.max_result_chars),
            SESSION_RETENTION_ENV_KEYS["preview_chars"]: str(policy.preview_chars),
        }
        os.environ.update(values)
        update_env_file_values(values, env_path)
        return get_session_retention_config_record(env_path=env_path, include_preview=True)
    except Exception as exc:
        logger.error("保存会话保留策略失败: %s", exc)
        raise AppConfigServiceError(500, f"保存会话保留策略失败: {exc}") from exc


def run_session_retention_policy_record() -> dict[str, Any]:
    try:
        from core.memory import memory_db

        return memory_db.apply_session_retention(dry_run=False)
    except Exception as exc:
        logger.error("执行会话保留策略失败: %s", exc)
        raise AppConfigServiceError(500, f"执行会话保留策略失败: {exc}") from exc


def get_session_retention_status_record(interval_seconds: int | None = None) -> dict[str, Any]:
    try:
        from core.memory import memory_db

        return memory_db.get_session_retention_status(interval_seconds=interval_seconds)
    except Exception as exc:
        logger.error("读取会话保留策略状态失败: %s", exc)
        return {
            "last_run": None,
            "next_run_at": None,
            "interval_seconds": interval_seconds,
            "error": str(exc),
        }


def preview_session_retention_policy(policy: SessionRetentionPolicy | None = None) -> dict[str, Any]:
    try:
        from core.memory import memory_db

        return memory_db.apply_session_retention(policy=policy, dry_run=True)
    except Exception as exc:
        logger.error("预览会话保留策略失败: %s", exc)
        return {"error": str(exc), "rows_scanned": 0, "rows_compacted": 0, "rows_deleted": 0}


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
