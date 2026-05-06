from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, MutableMapping
from typing import Any

from core.chat_runs import ChatRun, cancel_chat_run, start_chat_run

ChatStreamFactory = Callable[[], AsyncIterator[str]]
StartChatRun = Callable[[str, ChatStreamFactory], ChatRun]
StopChatRun = Callable[[str], bool]
STOP_AUDIT_MEMORY_TYPE = "manual_stop"


class ChatSessionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def start_session_chat_run(
    active_sessions: MutableMapping[str, dict[str, Any]],
    session_id: str,
    stream_factory: ChatStreamFactory,
    *,
    start_run: StartChatRun = start_chat_run,
    now: Callable[[], float] = time.time,
) -> ChatRun:
    if session_id not in active_sessions:
        raise ChatSessionServiceError(401, "会话已过期或不存在，请重新连接")

    active_sessions[session_id]["info"]["last_active"] = now()
    return start_run(session_id, stream_factory)


def _resolve_cancel_flags(cancel_flags: MutableMapping[str, bool] | None = None) -> MutableMapping[str, bool]:
    if cancel_flags is not None:
        return cancel_flags
    from core.agent import cancel_flags as default_cancel_flags

    return default_cancel_flags


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    if memory_db is not None:
        return memory_db
    from core.memory import memory_db as default_memory_db

    return default_memory_db


def build_manual_stop_audit_message(*, now: Callable[[], float] = time.time) -> dict[str, Any]:
    return {
        "role": "system",
        "content": "本轮任务已手动停止。停止请求已记录，后台会尽快回收正在执行的模型或工具任务。",
        "memory_type": STOP_AUDIT_MEMORY_TYPE,
        "audit_event": "manual_stop",
        "visible_to_user": True,
        "timestamp": int(now() * 1000),
    }


def _record_stop_audit_message(
    active_sessions: MutableMapping[str, dict[str, Any]] | None,
    session_id: str,
    *,
    memory_db: Any | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any] | None:
    if not active_sessions or session_id not in active_sessions:
        return None
    message = build_manual_stop_audit_message(now=now)
    info = active_sessions[session_id].setdefault("info", {})
    info.setdefault("pending_messages", []).append(message)
    store = _resolve_memory_db(memory_db)
    store.append_message(session_id, message)
    return message


def request_session_stop(
    session_id: str,
    cancel_flags: MutableMapping[str, bool] | None = None,
    *,
    active_sessions: MutableMapping[str, dict[str, Any]] | None = None,
    memory_db: Any | None = None,
    now: Callable[[], float] = time.time,
    stop_run: StopChatRun | None = None,
) -> dict[str, Any] | None:
    _resolve_cancel_flags(cancel_flags)[session_id] = True
    (stop_run or cancel_chat_run)(session_id)
    return _record_stop_audit_message(
        active_sessions,
        session_id,
        memory_db=memory_db,
        now=now,
    )
