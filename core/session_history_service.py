from __future__ import annotations

from typing import Any

from core.session_history import (
    build_session_history_markdown,
    clear_session_history,
    delete_session_message,
    get_user_visible_session_history,
    update_session_message_content,
)


class SessionHistoryServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_session_history_messages(memory_db: Any, session_id: str) -> list[dict]:
    try:
        return get_user_visible_session_history(memory_db, session_id)
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def clear_session_history_messages(memory_db: Any, session_id: str) -> None:
    try:
        clear_session_history(memory_db, session_id)
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def update_session_history_message_record(
    memory_db: Any,
    session_id: str,
    message_id: int,
    content: str,
) -> dict:
    try:
        return update_session_message_content(memory_db, session_id, message_id, content)
    except ValueError as exc:
        raise SessionHistoryServiceError(404, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def delete_session_history_message_record(
    memory_db: Any,
    session_id: str,
    message_id: int,
) -> None:
    try:
        delete_session_message(memory_db, session_id, message_id)
    except ValueError as exc:
        raise SessionHistoryServiceError(404, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def export_session_history_markdown_record(
    memory_db: Any,
    active_sessions: dict[str, dict],
    session_id: str,
) -> str:
    try:
        markdown = build_session_history_markdown(memory_db, active_sessions, session_id)
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc
    if not markdown:
        raise SessionHistoryServiceError(404, "该会话没有可导出的历史记录。")
    return markdown
