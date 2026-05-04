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


def _message_preview(message: dict, limit: int = 160) -> str:
    content = str(message.get("content") or message.get("text") or "").strip()
    content = " ".join(content.split())
    if len(content) <= limit:
        return content
    return content[:limit].rstrip() + "..."


def _memory_refs(message: dict) -> list[dict]:
    refs = message.get("memory_refs") or message.get("memoryRefs") or []
    return refs if isinstance(refs, list) else []


def _pending_conflict_matches_session(row: dict, session_id: str) -> bool:
    return (
        row.get("source_session_id") == session_id
        or row.get("scope_id") == session_id
        or f"sessions/{session_id}/" in str(row.get("path") or "")
    )


def build_session_memory_activity(memory_db, session_id: str) -> dict:
    messages = memory_db.get_messages(session_id, for_ui=True)
    referenced: list[dict] = []
    feedback_rows: list[dict] = []

    for message in messages:
        refs = _memory_refs(message)
        if refs:
            referenced.append(
                {
                    "message_id": message.get("_memory_id") or message.get("id"),
                    "created_at": message.get("created_at") or message.get("timestamp"),
                    "message_preview": _message_preview(message),
                    "refs": refs,
                }
            )

        feedback = message.get("feedback") or {}
        rating = feedback.get("rating") if isinstance(feedback, dict) else None
        if rating in {"up", "down"}:
            feedback_rows.append(
                {
                    "message_id": message.get("_memory_id") or message.get("id"),
                    "created_at": feedback.get("created_at")
                    or message.get("created_at")
                    or message.get("timestamp"),
                    "rating": rating,
                    "note": feedback.get("note") or "",
                    "message_preview": _message_preview(message),
                }
            )

    pending_conflicts: list[dict] = []
    list_pending = getattr(memory_db, "list_pending_memory_conflicts", None)
    if callable(list_pending):
        try:
            pending_rows = list_pending(limit=100)
        except TypeError:
            pending_rows = list_pending()
        pending_conflicts = [
            row
            for row in pending_rows
            if isinstance(row, dict) and _pending_conflict_matches_session(row, session_id)
        ]

    return {
        "session_id": session_id,
        "summary": {
            "referenced_count": sum(len(row.get("refs") or []) for row in referenced),
            "referenced_messages": len(referenced),
            "promoted_count": sum(1 for row in feedback_rows if row.get("rating") == "up"),
            "rejected_count": sum(1 for row in feedback_rows if row.get("rating") == "down"),
            "pending_conflict_count": len(pending_conflicts),
        },
        "referenced": referenced,
        "feedback": feedback_rows,
        "pending_conflicts": pending_conflicts,
    }
