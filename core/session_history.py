from __future__ import annotations


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


def delete_session_message(memory_db, session_id: str, message_id: int) -> None:
    memory_db.delete_message(session_id, message_id)
