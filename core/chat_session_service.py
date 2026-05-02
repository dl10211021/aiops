from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, MutableMapping
from typing import Any

from core.chat_runs import ChatRun, start_chat_run

ChatStreamFactory = Callable[[], AsyncIterator[str]]
StartChatRun = Callable[[str, ChatStreamFactory], ChatRun]


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


def request_session_stop(session_id: str, cancel_flags: MutableMapping[str, bool] | None = None) -> None:
    _resolve_cancel_flags(cancel_flags)[session_id] = True
