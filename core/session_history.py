from __future__ import annotations

import json
from collections.abc import Mapping

from core.session_export import format_session_history_markdown
from core.run_trace_store import RUN_TRACE_MEMORY_TYPE
from core.tool_registry import tool_policy_metadata
from core.tool_trace_policy import trace_command_actions, trace_command_primary_action


USER_VISIBLE_ROLES = {"user", "assistant"}
USER_VISIBLE_SYSTEM_MEMORY_TYPES = {"manual_stop"}


def get_user_visible_session_history(
    memory_db,
    session_id: str,
    limit: int | None = None,
) -> list[dict]:
    try:
        messages = memory_db.get_messages(session_id, for_ui=True, limit=limit)
    except TypeError:
        messages = memory_db.get_messages(session_id, for_ui=True)
        if limit and limit > 0:
            messages = messages[-limit:]
    messages = attach_legacy_exec_traces(messages)
    return [msg for msg in messages if is_user_visible_history_message(msg)]


def find_session_exec_trace(
    memory_db,
    session_id: str,
    *,
    evidence_id: str = "",
    tool_call_id: str = "",
    tool: str = "",
    limit: int = 200,
) -> dict | None:
    evidence_id = str(evidence_id or "").strip()
    tool_call_id = str(tool_call_id or "").strip()
    tool = str(tool or "").strip()
    if not any([evidence_id, tool_call_id, tool]):
        raise ValueError("必须提供 evidence_id、tool_call_id 或 tool")

    messages = get_user_visible_session_history(memory_db, session_id, limit=limit)
    for message in messages:
        traces = message.get("exec_trace") or message.get("execTrace") or []
        if not isinstance(traces, list):
            continue
        for trace in traces:
            if not isinstance(trace, dict):
                continue
            if _exec_trace_matches(trace, evidence_id=evidence_id, tool_call_id=tool_call_id, tool=tool):
                return {
                    "trace": trace,
                    "message": {
                        "id": message.get("_memory_id") or message.get("id"),
                        "role": message.get("role"),
                        "created_at": message.get("created_at") or message.get("timestamp"),
                        "preview": _message_preview(message),
                    },
                }
    return None


def list_session_run_trace_events(
    memory_db,
    session_id: str,
    *,
    limit: int = 200,
    run_id: str = "",
) -> list[dict]:
    try:
        limit = max(1, min(int(limit or 200), 500))
    except (TypeError, ValueError):
        limit = 200
    try:
        messages = memory_db.get_messages(session_id, for_ui=True, limit=limit)
    except TypeError:
        messages = memory_db.get_messages(session_id, for_ui=True)
        messages = messages[-limit:]

    target_run_id = str(run_id or "").strip()
    events: list[dict] = []
    for message in messages:
        if message.get("memory_type") != RUN_TRACE_MEMORY_TYPE:
            continue
        payload = message.get("run_event_payload")
        event_run_id = message.get("run_id") or (payload.get("run_id") if isinstance(payload, dict) else "")
        if target_run_id and event_run_id != target_run_id:
            continue
        events.append(
            {
                "id": message.get("_memory_id") or message.get("id"),
                "created_at": message.get("created_at") or message.get("timestamp"),
                "run_id": event_run_id,
                "event_type": message.get("run_event_type") or "",
                "event_ts": message.get("run_event_ts"),
                "payload": payload if isinstance(payload, dict) else {},
                "summary": message.get("content") or "",
            }
        )
    return events[-limit:]


def summarize_session_run_trace_events(events: list[dict]) -> list[dict]:
    runs_by_id: dict[str, dict] = {}
    ordered_runs: list[dict] = []
    for index, event in enumerate(events):
        run_id = str(event.get("run_id") or (event.get("payload") or {}).get("run_id") or "").strip()
        if not run_id:
            run_id = f"ungrouped-{event.get('event_ts') or event.get('created_at') or index}"
        run = runs_by_id.get(run_id)
        if run is None:
            run = {
                "run_id": run_id,
                "started_at": None,
                "ended_at": None,
                "duration_ms": None,
                "status": "running",
                "reason": "",
                "event_count": 0,
                "tool_count": 0,
                "step_count": 0,
                "latest_event_type": "",
                "latest_summary": "",
            }
            runs_by_id[run_id] = run
            ordered_runs.append(run)

        event_type = str(event.get("event_type") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        event_time = event.get("event_ts") or event.get("created_at")
        run["event_count"] += 1
        run["latest_event_type"] = event_type
        run["latest_summary"] = event.get("summary") or ""
        if event_type == "run:start":
            run["started_at"] = event_time
            run["status"] = "running"
        elif event_type == "run:end":
            run["ended_at"] = event_time
            run["status"] = str(payload.get("status") or "completed").lower()
            run["reason"] = str(payload.get("reason") or payload.get("error") or "").strip()
            run["duration_ms"] = _run_trace_duration_ms(run["started_at"], event_time)
        elif event_type == "agent:step":
            run["step_count"] += 1
        elif event_type.startswith("tool:"):
            run["tool_count"] += 1
    return ordered_runs


def build_session_run_learning_preview(
    memory_db,
    session_id: str,
    *,
    limit: int = 200,
    run_id: str = "",
) -> dict:
    events = list_session_run_trace_events(memory_db, session_id, limit=limit, run_id=run_id)
    runs = summarize_session_run_trace_events(events)
    tool_events = [event for event in events if event.get("event_type") == "tool:after"]
    evidence_refs = _run_trace_evidence_refs(tool_events)
    selected_run_id = str(run_id or "").strip()
    if not selected_run_id and len(runs) == 1:
        selected_run_id = str(runs[0].get("run_id") or "")
    title_suffix = f" {selected_run_id}" if selected_run_id else ""
    status_counts = _run_trace_tool_status_counts(tool_events)
    return {
        "session_id": session_id,
        "run_id": selected_run_id,
        "source": "session_run_trace",
        "candidate_type": "runbook",
        "eligible": bool(events and evidence_refs),
        "title": f"会话运行经验候选{title_suffix}".strip(),
        "summary": _run_trace_learning_summary(runs, tool_events, status_counts),
        "event_count": len(events),
        "run_count": len(runs),
        "tool_count": len(tool_events),
        "status_counts": status_counts,
        "evidence_refs": evidence_refs,
        "draft": {
            "title": f"Runbook 候选{title_suffix}".strip(),
            "outline": [
                "适用场景：来自会话 Run Trace 的一次运维执行过程。",
                "执行步骤：按工具证据复核关键命令、查询和结果。",
                "验证方式：确认工具状态、证据 ID、审批记录和最终运行状态。",
                "风险边界：发布前需要人工确认适用系统、权限要求和回滚条件。",
            ],
        },
        "next_action": "在知识库学习候选池中人工确认后，再发布为 Runbook 或 Skill。",
    }


def _run_trace_evidence_refs(tool_events: list[dict]) -> list[dict]:
    refs: list[dict] = []
    seen: set[str] = set()
    for event in tool_events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        evidence_id = str(payload.get("evidence_id") or "").strip()
        tool_call_id = str(payload.get("tool_call_id") or "").strip()
        ref_id = evidence_id or tool_call_id
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        tool_name = str(payload.get("tool_name") or "").strip()
        refs.append(
            {
                "type": "tool_evidence" if evidence_id else "tool_trace",
                "label": "工具证据" if evidence_id else "执行轨迹",
                "id": ref_id,
                "tool": tool_name,
                "status": str(payload.get("status") or "").strip(),
                "event_id": event.get("id"),
            }
        )
    return refs


def _run_trace_tool_status_counts(tool_events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in tool_events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        status = str(payload.get("status") or "unknown").strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _run_trace_learning_summary(
    runs: list[dict],
    tool_events: list[dict],
    status_counts: dict[str, int],
) -> str:
    if not runs and not tool_events:
        return "未找到可用于学习的运行轨迹。"
    latest = runs[-1] if runs else {}
    status = latest.get("status") or "unknown"
    parts = [
        f"运行状态 {status}",
        f"工具调用 {len(tool_events)} 次",
    ]
    if status_counts:
        parts.append("结果分布 " + ", ".join(f"{key}:{value}" for key, value in sorted(status_counts.items())))
    if latest.get("reason"):
        parts.append(f"原因 {latest.get('reason')}")
    return "；".join(parts) + "。"


def _run_trace_duration_ms(started_at: object, ended_at: object) -> int | None:
    if not isinstance(started_at, (int, float)) or not isinstance(ended_at, (int, float)):
        return None
    duration = max(0.0, (float(ended_at) - float(started_at)) * 1000.0)
    return int(round(duration))


def _exec_trace_matches(
    trace: Mapping,
    *,
    evidence_id: str = "",
    tool_call_id: str = "",
    tool: str = "",
) -> bool:
    evidence = trace.get("evidence") if isinstance(trace.get("evidence"), Mapping) else {}
    trace_evidence_ids = {
        str(trace.get("evidenceId") or "").strip(),
        str(trace.get("evidence_id") or "").strip(),
        str(evidence.get("evidence_id") or "").strip(),
    }
    trace_tool_call_ids = {
        str(trace.get("toolCallId") or "").strip(),
        str(trace.get("tool_call_id") or "").strip(),
    }
    if evidence_id and evidence_id in trace_evidence_ids:
        return True
    if tool_call_id and tool_call_id in trace_tool_call_ids:
        return True
    return bool(tool and str(trace.get("tool") or "").strip() == tool)


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
        result_meta = _legacy_result_meta(result, tool_name, args)
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


def _legacy_result_meta(result: str, tool_name: str = "", args: object = "") -> dict:
    try:
        parsed = json.loads(result)
    except Exception:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    if tool_name and not parsed.get("tool_policy"):
        parsed = {**parsed, "tool_policy": tool_policy_metadata(tool_name)}
    trace = {"tool": tool_name, "args": args, "resultMeta": parsed}
    primary_action = trace_command_primary_action(trace)
    if primary_action and not parsed.get("primary_action"):
        parsed = {**parsed, "primary_action": primary_action}
    actions = trace_command_actions(trace)
    if actions and not parsed.get("actions"):
        parsed = {**parsed, "actions": actions}
    return parsed


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
                "pending_review" if rating == "up" else "do_not_promote_answer"
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
            "promoted_count": sum(1 for row in feedback_rows if row.get("memory_policy") == "promote"),
            "pending_candidate_count": sum(1 for row in feedback_rows if row.get("memory_policy") == "pending_review"),
            "rejected_count": sum(1 for row in feedback_rows if row.get("rating") == "down"),
            "pending_conflict_count": len(pending_conflicts),
        },
        "referenced": referenced,
        "feedback": feedback_rows,
        "pending_conflicts": pending_conflicts,
    }
