from __future__ import annotations

from typing import Any

from core import memory as memory_module
from core.session_history import (
    build_session_memory_activity,
    build_session_history_markdown,
    clear_session_history,
    delete_session_message,
    get_user_visible_session_history,
    update_session_message_content,
    update_session_message_feedback,
)


class SessionHistoryServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_memory_db(memory_db: Any | None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def list_session_history_messages(
    session_id: str,
    limit: int | None = None,
    memory_db: Any | None = None,
) -> list[dict]:
    try:
        return get_user_visible_session_history(
            _resolve_memory_db(memory_db),
            session_id,
            limit=limit,
        )
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def clear_session_history_messages(
    session_id: str,
    memory_db: Any | None = None,
) -> None:
    try:
        clear_session_history(_resolve_memory_db(memory_db), session_id)
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def update_session_history_message_record(
    session_id: str,
    message_id: int,
    content: str,
    memory_db: Any | None = None,
) -> dict:
    try:
        return update_session_message_content(
            _resolve_memory_db(memory_db),
            session_id,
            message_id,
            content,
        )
    except ValueError as exc:
        raise SessionHistoryServiceError(404, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def update_session_history_message_feedback_record(
    session_id: str,
    message_id: int,
    rating: str,
    note: str | None = None,
    memory_db: Any | None = None,
) -> dict:
    try:
        return update_session_message_feedback(
            _resolve_memory_db(memory_db),
            session_id,
            message_id,
            rating,
            note,
        )
    except ValueError as exc:
        raise SessionHistoryServiceError(404, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def delete_session_history_message_record(
    session_id: str,
    message_id: int,
    memory_db: Any | None = None,
) -> None:
    try:
        delete_session_message(_resolve_memory_db(memory_db), session_id, message_id)
    except ValueError as exc:
        raise SessionHistoryServiceError(404, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def export_session_history_markdown_record(
    active_sessions: dict[str, dict],
    session_id: str,
    memory_db: Any | None = None,
) -> str:
    try:
        markdown = build_session_history_markdown(
            _resolve_memory_db(memory_db),
            active_sessions,
            session_id,
        )
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc
    if not markdown:
        raise SessionHistoryServiceError(404, "该会话没有可导出的历史记录。")
    return markdown


def get_session_memory_activity_record(
    session_id: str,
    memory_db: Any | None = None,
) -> dict:
    try:
        return build_session_memory_activity(_resolve_memory_db(memory_db), session_id)
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc
