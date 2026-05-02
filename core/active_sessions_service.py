from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from core import chat_runs as chat_runs_module
from core import memory as memory_module
from core.session_views import build_active_sessions_response


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def _resolve_is_session_streaming(is_session_streaming: Callable[[str], bool] | None = None) -> Callable[[str], bool]:
    return is_session_streaming if is_session_streaming is not None else chat_runs_module.is_chat_running


def build_active_sessions_payload(
    active_sessions: Mapping[str, dict],
    *,
    is_session_streaming: Callable[[str], bool] | None = None,
    memory_db: Any | None = None,
) -> dict[str, dict[str, Any]]:
    store = _resolve_memory_db(memory_db)
    return build_active_sessions_response(
        active_sessions,
        is_session_streaming=_resolve_is_session_streaming(is_session_streaming),
        sensitive_keys=store.sensitive_keys,
    )
