from __future__ import annotations

from typing import Any

from core import memory as memory_module
from core.session_history import (
    build_session_run_learning_preview,
    build_session_memory_activity,
    build_session_history_markdown,
    clear_session_history,
    delete_session_message,
    find_session_exec_trace,
    get_user_visible_session_history,
    list_session_run_trace_events,
    summarize_session_run_trace_events,
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


def find_session_history_evidence_trace(
    session_id: str,
    *,
    evidence_id: str = "",
    tool_call_id: str = "",
    tool: str = "",
    limit: int = 200,
    memory_db: Any | None = None,
) -> dict:
    try:
        result = find_session_exec_trace(
            _resolve_memory_db(memory_db),
            session_id,
            evidence_id=evidence_id,
            tool_call_id=tool_call_id,
            tool=tool,
            limit=limit,
        )
    except ValueError as exc:
        raise SessionHistoryServiceError(400, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc
    if not result:
        raise SessionHistoryServiceError(404, "未找到匹配的工具证据。")
    return result


def get_session_run_trace_record(
    session_id: str,
    *,
    limit: int = 200,
    run_id: str = "",
    memory_db: Any | None = None,
) -> dict:
    try:
        events = list_session_run_trace_events(
            _resolve_memory_db(memory_db),
            session_id,
            limit=limit,
            run_id=run_id,
        )
        return {
            "events": events,
            "runs": summarize_session_run_trace_events(events),
        }
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def get_session_run_learning_preview_record(
    session_id: str,
    *,
    limit: int = 200,
    run_id: str = "",
    memory_db: Any | None = None,
) -> dict:
    try:
        return build_session_run_learning_preview(
            _resolve_memory_db(memory_db),
            session_id,
            limit=limit,
            run_id=run_id,
        )
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def create_session_run_learning_candidate_record(
    session_id: str,
    *,
    run_id: str = "",
    actor: str = "user",
    reason: str = "人工提交 Run Trace 学习候选",
    memory_db: Any | None = None,
) -> dict:
    try:
        resolved_db = _resolve_memory_db(memory_db)
        preview = build_session_run_learning_preview(
            resolved_db,
            session_id,
            limit=300,
            run_id=run_id,
        )
        if not preview.get("eligible"):
            raise SessionHistoryServiceError(400, "当前 Run Trace 缺少工具证据，不能提交学习候选。")
        store = getattr(resolved_db, "file_memory_store", None)
        if store is None:
            raise SessionHistoryServiceError(500, "记忆候选池不可用。")

        source_run_id = str(preview.get("run_id") or run_id or "all").strip() or "all"
        existing = _existing_run_learning_candidate(store, session_id=session_id, run_id=source_run_id)
        if existing:
            return {
                "candidate": None,
                "learning_candidate": existing,
                "version": None,
                "preview": preview,
                "deduped": True,
            }

        summary = _run_learning_candidate_summary(preview)
        version = store.append_memory(
            scope_id=session_id,
            summary=summary,
            source_session_id=session_id,
            metadata={
                "source": "run_trace_learning_preview",
                "memory_kind": "success_experience",
                "candidate_type": "run_trace_runbook_preview",
                "review_status": "pending",
                "retrieval_enabled": False,
                "run_id": source_run_id,
                "submit_reason": reason,
                "source_refs": [
                    {"type": "session", "label": "来源会话", "id": session_id},
                    {"type": "run_trace", "label": "Run Trace", "id": preview.get("run_id") or run_id or "all"},
                ],
                "evidence_refs": preview.get("evidence_refs") or [],
            },
        )
        candidate = _latest_run_learning_candidate(store, session_id=session_id)
        if not candidate:
            raise SessionHistoryServiceError(500, "学习候选写入后未能定位。")
        promoted = store.resolve_candidate_entry(candidate["candidate_id"], "to_runbook", actor=actor)
        return {
            "candidate": candidate,
            "learning_candidate": promoted.get("learning_candidate"),
            "version": version,
            "preview": preview,
        }
    except SessionHistoryServiceError:
        raise
    except ValueError as exc:
        raise SessionHistoryServiceError(400, str(exc)) from exc
    except Exception as exc:
        raise SessionHistoryServiceError(500, str(exc)) from exc


def _run_learning_candidate_summary(preview: dict) -> str:
    outline = preview.get("draft", {}).get("outline") if isinstance(preview.get("draft"), dict) else []
    lines = [
        "【记忆类型】Run Trace 学习候选",
        "【候选状态】待人工确认",
        "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
        f"【核心记忆】{preview.get('summary') or 'Run Trace 可沉淀为运维 Runbook 候选。'}",
        f"【运行范围】run_id={preview.get('run_id') or 'all'}；事件={preview.get('event_count') or 0}；工具={preview.get('tool_count') or 0}；证据={len(preview.get('evidence_refs') or [])}",
    ]
    if isinstance(outline, list) and outline:
        lines.append("【草稿大纲】")
        lines.extend(f"- {item}" for item in outline[:8] if str(item or "").strip())
    lines.append("【使用提醒】人工确认并补齐质量清单后才可整理为 Runbook；使用前仍需结合当前资产实时工具结果验证。")
    return "\n".join(lines)


def _latest_run_learning_candidate(store: Any, *, session_id: str) -> dict | None:
    candidates = store.list_candidate_entries(
        limit=20,
        review_statuses=["pending"],
    )
    for item in candidates:
        if (
            item.get("source_session_id") == session_id
            and item.get("candidate_type") == "run_trace_runbook_preview"
        ):
            return item
    return None


def _existing_run_learning_candidate(store: Any, *, session_id: str, run_id: str) -> dict | None:
    list_candidates = getattr(store, "list_learning_candidates", None)
    if not callable(list_candidates):
        return None
    for item in list_candidates(limit=200, target_type="runbook"):
        if (
            item.get("source_session_id") == session_id
            and str(item.get("run_id") or "") == run_id
            and str(item.get("status") or "") != "rejected"
        ):
            return item
    return None


def list_session_run_trace_records(
    session_id: str,
    *,
    limit: int = 200,
    run_id: str = "",
    memory_db: Any | None = None,
) -> list[dict]:
    return get_session_run_trace_record(
        session_id,
        limit=limit,
        run_id=run_id,
        memory_db=memory_db,
    )["events"]


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
