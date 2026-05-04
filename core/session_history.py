from __future__ import annotations

from collections.abc import Mapping

from core.session_export import format_session_history_markdown


USER_VISIBLE_ROLES = {"user", "assistant"}


def get_user_visible_session_history(memory_db, session_id: str) -> list[dict]:
    messages = memory_db.get_messages(session_id, for_ui=True)
    return [msg for msg in messages if msg.get("role") in USER_VISIBLE_ROLES]


def clear_session_history(memory_db, session_id: str) -> None:
    memory_db.clear_history(session_id)


def update_session_message_content(
    memory_db,
    session_id: str,
    message_id: int,
    content: str,
) -> dict:
    return memory_db.update_message_content(session_id, message_id, content)


def update_session_message_feedback(
    memory_db,
    session_id: str,
    message_id: int,
    rating: str,
    note: str | None = None,
) -> dict:
    return memory_db.update_message_feedback(session_id, message_id, rating, note)


def delete_session_message(memory_db, session_id: str, message_id: int) -> None:
    memory_db.delete_message(session_id, message_id)


def session_history_export_title(
    active_sessions: Mapping[str, dict],
    session_id: str,
) -> str:
    remark = ""
    if session_id in active_sessions:
        remark = active_sessions[session_id]["info"].get("remark", "")
    return remark or session_id


def build_session_history_markdown(
    memory_db,
    active_sessions: Mapping[str, dict],
    session_id: str,
) -> str:
    messages = memory_db.get_messages(session_id, for_ui=True)
    return format_session_history_markdown(
        messages,
        session_history_export_title(active_sessions, session_id),
    )
