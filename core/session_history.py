from __future__ import annotations

import json
from collections.abc import Mapping

from core.session_export import format_session_history_markdown


USER_VISIBLE_ROLES = {"user", "assistant"}
USER_VISIBLE_SYSTEM_MEMORY_TYPES = {"manual_stop"}


def get_user_visible_session_history(memory_db, session_id: str) -> list[dict]:
    messages = memory_db.get_messages(session_id, for_ui=True)
    messages = attach_legacy_exec_traces(messages)
    return [msg for msg in messages if is_user_visible_history_message(msg)]


def is_user_visible_history_message(message: Mapping) -> bool:
    role = message.get("role")
    if role in USER_VISIBLE_ROLES:
        return True
    return (
        role == "system"
        and bool(message.get("visible_to_user"))
        and message.get("memory_type") in USER_VISIBLE_SYSTEM_MEMORY_TYPES
    )


def attach_legacy_exec_traces(messages: list[dict]) -> list[dict]:
    """Rebuild UI execution traces from legacy assistant/tool message pairs.

    Older chat turns stored OpenAI-style ``tool_calls`` on assistant messages and
    the corresponding tool result rows, but did not persist the derived
    ``exec_trace`` list that the right-side AI thinking panel reads. Keep the
    durable rows untouched and synthesize trace metadata only for UI/history
    responses when it is missing.
    """
    tool_results = {
        str(message.get("tool_call_id") or ""): message
        for message in messages
        if message.get("role") == "tool" and message.get("tool_call_id")
    }
    if not tool_results:
        return messages

    hydrated: list[dict] = []
    for message in messages:
        next_message = dict(message)
        if (
            next_message.get("role") == "assistant"
            and not (next_message.get("exec_trace") or next_message.get("execTrace"))
        ):
            traces = _legacy_exec_traces_for_message(next_message, tool_results)
            if traces:
                next_message["exec_trace"] = traces
        hydrated.append(next_message)
    return hydrated


def _legacy_exec_traces_for_message(
    message: dict,
    tool_results: dict[str, dict],
) -> list[dict]:
    traces: list[dict] = []
    tool_calls = message.get("tool_calls") or []
    if not isinstance(tool_calls, list):
        return traces
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        call_id = str(call.get("id") or "")
        function = call.get("function") if isinstance(call.get("function"), dict) else {}
        tool_name = str(function.get("name") or call.get("name") or "unknown")
        args = function.get("arguments") if function else call.get("arguments")
        result_message = tool_results.get(call_id)
        result = str((result_message or {}).get("content") or "")
        result_meta = _legacy_result_meta(result)
        traces.append(
            {
                "type": "tool_end",
                "tool": tool_name,
                "args": str(args or ""),
                "result": result,
                "resultMeta": result_meta,
                "status": _legacy_trace_status(result_meta),
            }
        )
    return traces


def _legacy_result_meta(result: str) -> dict:
    try:
        parsed = json.loads(result)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _legacy_trace_status(result_meta: dict) -> str:
    raw_status = str(result_meta.get("status") or "").lower()
    if raw_status in {"error", "failed", "blocked"}:
        return "error"
    if result_meta.get("success") is False or result_meta.get("has_error") is True:
        return "error"
    if result_meta.get("error") or result_meta.get("raw_error"):
        return "error"
    return "done"


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
            memory_policy = feedback.get("memory_policy") or (
                "promote" if rating == "up" else "do_not_promote_answer"
            )
            feedback_rows.append(
                {
                    "message_id": message.get("_memory_id") or message.get("id"),
                    "created_at": feedback.get("created_at")
                    or message.get("created_at")
                    or message.get("timestamp"),
                    "rating": rating,
                    "note": feedback.get("note") or "",
                    "memory_policy": memory_policy,
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

    feedback_corrections = [
        {
            "version_id": f"feedback-{session_id}-{row.get('message_id') or 'unknown'}",
            "path": f"sessions/{session_id}/feedback/{row.get('message_id') or 'unknown'}",
            "operation": "negative_feedback",
            "source_session_id": session_id,
            "scope_id": session_id,
            "message_id": row.get("message_id"),
            "created_at": row.get("created_at"),
            "reason": row.get("note") or "用户点踩该回答，需要纠错审计。",
            "recommended_action": "复核该回答的事实、证据和建议；确认不写入成功经验，必要时整理为纠错记忆。",
            "message_preview": row.get("message_preview") or "",
            "status": "pending_feedback_review",
        }
        for row in feedback_rows
        if row.get("rating") == "down"
    ]
    pending_conflicts.extend(feedback_corrections)

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
