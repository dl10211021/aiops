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


def summarize_session_run_trace_audit(events: list[dict]) -> dict:
    runs = summarize_session_run_trace_events(events)
    events_by_run: dict[str, list[dict]] = {}
    for index, event in enumerate(events):
        run_id = str(event.get("run_id") or (event.get("payload") or {}).get("run_id") or "").strip()
        if not run_id:
            run_id = f"ungrouped-{event.get('event_ts') or event.get('created_at') or index}"
        events_by_run.setdefault(run_id, []).append(event)

    summary = {
        "run_count": len(runs),
        "event_count": len(events),
        "audited_run_count": 0,
        "unaudited_run_count": 0,
        "context_sources": 0,
        "context_hits": 0,
        "context_errors": 0,
        "prompt_modules": 0,
        "runtime_tool_count": 0,
        "runtime_success_count": 0,
        "runtime_error_count": 0,
        "runtime_timeout_count": 0,
        "runtime_retry_count": 0,
        "runtime_concurrent_count": 0,
        "runtime_untracked_count": 0,
        "source_counts": {},
        "module_counts": {},
        "runtime_error_types": {},
    }
    for run in runs:
        run_events = events_by_run.get(str(run.get("run_id") or ""), [])
        context = _run_trace_audit_context(run_events)
        context_sources = _run_trace_context_sources(context)
        prompt_manifest = _run_trace_prompt_manifest(context)
        runtime_audit = _run_trace_runtime_audit(run_events)
        has_audit = bool(context_sources or prompt_manifest.get("modules"))
        if has_audit:
            summary["audited_run_count"] += 1
        else:
            summary["unaudited_run_count"] += 1

        for key in (
            "runtime_tool_count",
            "runtime_success_count",
            "runtime_error_count",
            "runtime_timeout_count",
            "runtime_retry_count",
            "runtime_concurrent_count",
            "runtime_untracked_count",
        ):
            summary[key] += runtime_audit[key]
        _merge_flat_count_map(summary["runtime_error_types"], runtime_audit["runtime_error_types"])

        for source in context_sources:
            source_id = source["source"]
            summary["context_sources"] += 1
            if source["enabled"] and source["hit"]:
                summary["context_hits"] += 1
            if source["status"] == "error":
                summary["context_errors"] += 1
            source_counts = summary["source_counts"].setdefault(
                source_id,
                {"total": 0, "hit": 0, "error": 0, "disabled": 0},
            )
            source_counts["total"] += 1
            if source["hit"]:
                source_counts["hit"] += 1
            if source["status"] == "error":
                source_counts["error"] += 1
            if not source["enabled"]:
                source_counts["disabled"] += 1

        for module in prompt_manifest.get("modules", []):
            module_id = str(module.get("module") or "").strip()
            if not module_id:
                continue
            summary["prompt_modules"] += 1
            module_counts = summary["module_counts"].setdefault(
                module_id,
                {"total": 0, "enabled": 0, "disabled": 0},
            )
            module_counts["total"] += 1
            if module.get("enabled") is False:
                module_counts["disabled"] += 1
            else:
                module_counts["enabled"] += 1
    return summary


def _run_trace_runtime_audit(events: list[dict]) -> dict:
    audit = {
        "runtime_tool_count": 0,
        "runtime_success_count": 0,
        "runtime_error_count": 0,
        "runtime_timeout_count": 0,
        "runtime_retry_count": 0,
        "runtime_concurrent_count": 0,
        "runtime_untracked_count": 0,
        "runtime_error_types": {},
    }
    for event in events:
        if event.get("event_type") != "tool:after":
            continue
        audit["runtime_tool_count"] += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        runtime = _run_trace_runtime_execution(payload)
        if not runtime:
            audit["runtime_untracked_count"] += 1
            continue
        final_status = _runtime_final_status(runtime, payload)
        error_type = str(runtime.get("error_type") or payload.get("error_type") or "").strip()
        if final_status == "success":
            audit["runtime_success_count"] += 1
        elif final_status == "error":
            audit["runtime_error_count"] += 1
            normalized_error = error_type or "tool_execution_failed"
            audit["runtime_error_types"][normalized_error] = audit["runtime_error_types"].get(normalized_error, 0) + 1
            if normalized_error == "tool_timeout":
                audit["runtime_timeout_count"] += 1
        if runtime.get("retried") is True or _runtime_attempts(runtime) > 1:
            audit["runtime_retry_count"] += 1
        if runtime.get("concurrent") is True:
            audit["runtime_concurrent_count"] += 1
    return audit


def _run_trace_runtime_execution(payload: dict) -> dict:
    result_meta = payload.get("result_meta") or payload.get("resultMeta")
    if isinstance(result_meta, dict):
        runtime = result_meta.get("runtime_execution") or result_meta.get("runtime_policy")
        if isinstance(runtime, dict):
            return runtime
    evidence = payload.get("evidence")
    if isinstance(evidence, dict):
        evidence_meta = evidence.get("result_meta") or evidence.get("resultMeta")
        if isinstance(evidence_meta, dict):
            runtime = evidence_meta.get("runtime_execution") or evidence_meta.get("runtime_policy")
            if isinstance(runtime, dict):
                return runtime
    return {}


def _runtime_final_status(runtime: dict, payload: dict) -> str:
    status = str(runtime.get("final_status") or payload.get("status") or "").strip().lower()
    if status in {"success", "ok", "done", "completed"}:
        return "success"
    if status in {"error", "failed", "failure", "blocked", "timeout"}:
        return "error"
    if runtime.get("error_type") or payload.get("error_type"):
        return "error"
    return status or "unknown"


def _runtime_attempts(runtime: dict) -> int:
    try:
        return int(runtime.get("attempts") or 0)
    except (TypeError, ValueError):
        return 0


def _merge_flat_count_map(target: dict[str, int], source: Mapping[str, int]) -> None:
    for key, value in source.items():
        try:
            target[str(key)] = target.get(str(key), 0) + int(value or 0)
        except (TypeError, ValueError):
            continue


def _run_trace_audit_context(events: list[dict]) -> dict:
    for event in events:
        if event.get("event_type") != "run:start":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        context = payload.get("context")
        if isinstance(context, dict):
            return context
    for event in events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        context = payload.get("context")
        if isinstance(context, dict):
            return context
    return {}


def _run_trace_context_sources(context: dict) -> list[dict]:
    sources = context.get("context_sources")
    if not isinstance(sources, list):
        return []
    normalized: list[dict] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source") or "").strip()
        if not source_id:
            continue
        try:
            reference_count = max(0, int(source.get("reference_count") or 0))
        except (TypeError, ValueError):
            reference_count = 0
        normalized.append(
            {
                "source": source_id,
                "enabled": source.get("enabled") is not False,
                "hit": source.get("hit") is True,
                "reference_count": reference_count,
                "status": str(source.get("status") or "ok"),
            }
        )
    return normalized


def _run_trace_prompt_manifest(context: dict) -> dict:
    manifest = context.get("prompt_modules")
    if not isinstance(manifest, dict):
        return {"modules": []}
    raw_modules = manifest.get("modules")
    if not isinstance(raw_modules, list):
        return {"modules": []}
    enabled_map = manifest.get("enabled") if isinstance(manifest.get("enabled"), dict) else {}
    modules = []
    for module in raw_modules:
        module_id = str(module or "").strip()
        if not module_id:
            continue
        modules.append({"module": module_id, "enabled": enabled_map.get(module_id) is not False})
    return {
        "surface": str(manifest.get("surface") or ""),
        "mode": str(manifest.get("mode") or ""),
        "modules": modules,
    }


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


def search_session_context(
    memory_db,
    session_id: str,
    *,
    query: str,
    limit: int = 50,
) -> dict:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise ValueError("搜索关键词不能为空")
    try:
        result_limit = max(1, min(int(limit or 50), 100))
    except (TypeError, ValueError):
        result_limit = 50
    terms = [term.lower() for term in normalized_query.split() if term.strip()]
    if not terms:
        raise ValueError("搜索关键词不能为空")

    results: list[dict] = []
    messages = get_user_visible_session_history(memory_db, session_id, limit=300)
    for message in messages:
        searchable = _searchable_message_text(message)
        if not _text_matches_terms(searchable, terms):
            continue
        results.append(
            {
                "type": "message",
                "session_id": session_id,
                "message_id": message.get("_memory_id") or message.get("id"),
                "role": message.get("role") or "",
                "created_at": message.get("created_at") or message.get("timestamp"),
                "title": _message_search_title(message),
                "preview": _message_preview(message),
                "score": _term_match_score(searchable, terms),
                "evidence_refs": _message_evidence_refs(message),
            }
        )

    for event in list_session_run_trace_events(memory_db, session_id, limit=300):
        searchable = _searchable_run_trace_text(event)
        if not _text_matches_terms(searchable, terms):
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        results.append(
            {
                "type": "run_trace",
                "session_id": session_id,
                "message_id": event.get("id"),
                "run_id": event.get("run_id") or payload.get("run_id") or "",
                "event_type": event.get("event_type") or "",
                "created_at": event.get("created_at"),
                "event_ts": event.get("event_ts"),
                "title": _run_trace_search_title(event),
                "preview": _run_trace_search_preview(event),
                "score": _term_match_score(searchable, terms),
                "evidence_refs": _run_trace_event_evidence_refs(event),
            }
        )

    results.sort(key=_session_search_sort_key, reverse=True)
    limited = results[:result_limit]
    by_type: dict[str, int] = {}
    for item in limited:
        item_type = str(item.get("type") or "unknown")
        by_type[item_type] = by_type.get(item_type, 0) + 1
    return {
        "query": normalized_query,
        "session_id": session_id,
        "limit": result_limit,
        "results": limited,
        "summary": {
            "total": len(limited),
            "matched_total": len(results),
            "by_type": by_type,
        },
    }


def _session_search_sort_key(item: Mapping) -> tuple[int, str]:
    return (
        int(item.get("score") or 0),
        str(item.get("created_at") or item.get("event_ts") or ""),
    )


def _searchable_message_text(message: Mapping) -> str:
    parts = [
        str(message.get("role") or ""),
        str(message.get("content") or ""),
    ]
    traces = message.get("exec_trace") or message.get("execTrace") or []
    if isinstance(traces, list):
        for trace in traces:
            if isinstance(trace, Mapping):
                parts.append(str(trace.get("tool") or ""))
                parts.append(json.dumps(trace, ensure_ascii=False, sort_keys=True))
    return "\n".join(parts).lower()


def _searchable_run_trace_text(event: Mapping) -> str:
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    return "\n".join(
        [
            str(event.get("run_id") or ""),
            str(event.get("event_type") or ""),
            str(event.get("summary") or ""),
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        ]
    ).lower()


def _text_matches_terms(text: str, terms: list[str]) -> bool:
    return all(term in text for term in terms)


def _term_match_score(text: str, terms: list[str]) -> int:
    return sum(text.count(term) for term in terms)


def _message_search_title(message: Mapping) -> str:
    role = str(message.get("role") or "message")
    message_id = message.get("_memory_id") or message.get("id") or ""
    return f"{role} #{message_id}".strip()


def _message_evidence_refs(message: Mapping) -> list[dict]:
    refs: list[dict] = []
    seen: set[str] = set()
    traces = message.get("exec_trace") or message.get("execTrace") or []
    if not isinstance(traces, list):
        return refs
    for trace in traces:
        if not isinstance(trace, Mapping):
            continue
        evidence = trace.get("evidence") if isinstance(trace.get("evidence"), Mapping) else {}
        evidence_id = str(
            trace.get("evidenceId")
            or trace.get("evidence_id")
            or evidence.get("evidence_id")
            or ""
        ).strip()
        tool_call_id = str(trace.get("toolCallId") or trace.get("tool_call_id") or "").strip()
        ref_id = evidence_id or tool_call_id
        if not ref_id or ref_id in seen:
            continue
        seen.add(ref_id)
        refs.append(
            {
                "type": "tool_evidence" if evidence_id else "tool_trace",
                "id": ref_id,
                "tool": str(trace.get("tool") or evidence.get("tool_name") or "").strip(),
                "status": str(trace.get("status") or evidence.get("result_status") or "").strip(),
            }
        )
    return refs


def _run_trace_search_title(event: Mapping) -> str:
    event_type = str(event.get("event_type") or "run_trace")
    run_id = str(event.get("run_id") or "").strip()
    return f"{event_type} {run_id}".strip()


def _run_trace_search_preview(event: Mapping) -> str:
    summary = str(event.get("summary") or "").strip()
    if summary:
        return summary[:240]
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)[:240]


def _run_trace_event_evidence_refs(event: Mapping) -> list[dict]:
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), Mapping) else {}
    evidence_id = str(payload.get("evidence_id") or evidence.get("evidence_id") or "").strip()
    tool_call_id = str(payload.get("tool_call_id") or evidence.get("tool_call_id") or "").strip()
    ref_id = evidence_id or tool_call_id
    if not ref_id:
        return []
    return [
        {
            "type": "tool_evidence" if evidence_id else "tool_trace",
            "id": ref_id,
            "tool": str(payload.get("tool_name") or payload.get("tool") or evidence.get("tool_name") or "").strip(),
            "status": str(payload.get("status") or evidence.get("result_status") or "").strip(),
        }
    ]
