from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from threading import RLock
from typing import Any
from uuid import uuid4

from core.redaction import redact_value
from core.run_hooks import register_run_hook

RUN_TRACE_MEMORY_TYPE = "aiops_run_trace"


def build_run_trace_message(
    event_type: str,
    payload: dict[str, Any],
    *,
    event_ts: float | None = None,
) -> dict[str, Any] | None:
    session_id = str((payload or {}).get("session_id") or "").strip()
    if not session_id:
        return None
    safe_payload = redact_value(payload or {})
    run_id = str(safe_payload.get("run_id") or "").strip()
    return {
        "role": "system",
        "content": _run_trace_content(event_type, safe_payload),
        "memory_type": RUN_TRACE_MEMORY_TYPE,
        "visible_to_user": False,
        "run_id": run_id,
        "run_event_type": event_type,
        "run_event_payload": safe_payload,
        "run_event_ts": event_ts or time.time(),
    }


def register_session_run_trace_hooks(memory_store: Any) -> Callable[[], None]:
    active_runs: dict[str, list[str]] = defaultdict(list)
    lock = RLock()

    def handler(event_type: str, payload: dict[str, Any]) -> None:
        event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        if not isinstance(event_payload, dict):
            return
        emitted_at = payload.get("emitted_at") if isinstance(payload, dict) else None
        event_ts = emitted_at if isinstance(emitted_at, (int, float)) else None
        event_payload = dict(event_payload)
        run_id = _assign_run_id(event_type, event_payload, active_runs, lock)
        event_payload["run_id"] = run_id
        message = build_run_trace_message(event_type, event_payload, event_ts=event_ts)
        if not message:
            return
        memory_store.append_message(message["run_event_payload"]["session_id"], message)

    unregister_all = register_run_hook("*", handler)
    return unregister_all


def _assign_run_id(
    event_type: str,
    payload: dict[str, Any],
    active_runs: dict[str, list[str]],
    lock: RLock,
) -> str:
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        return str(payload.get("run_id") or "").strip()

    with lock:
        existing = str(payload.get("run_id") or "").strip()
        stack = active_runs[session_id]
        if event_type == "run:start":
            run_id = existing or _new_run_id()
            stack.append(run_id)
            return run_id
        if event_type == "run:end":
            run_id = existing or (stack[-1] if stack else _new_run_id())
            if stack and stack[-1] == run_id:
                stack.pop()
            elif run_id in stack:
                stack.remove(run_id)
            if not stack:
                active_runs.pop(session_id, None)
            return run_id
        return existing or (stack[-1] if stack else _new_run_id())


def _new_run_id() -> str:
    return f"run_{uuid4().hex}"


def _run_trace_content(event_type: str, payload: dict[str, Any]) -> str:
    label = {
        "run:start": "运行开始",
        "agent:step": "Agent 步进",
        "tool:before": "工具开始",
        "tool:after": "工具结束",
        "run:end": "运行结束",
    }.get(event_type, event_type)
    details = []
    if payload.get("model_name"):
        details.append(f"模型={payload.get('model_name')}")
    if payload.get("iteration") is not None:
        details.append(f"step={payload.get('iteration')}")
    if payload.get("tool_name"):
        details.append(f"工具={payload.get('tool_name')}")
    if payload.get("status"):
        details.append(f"状态={payload.get('status')}")
    if payload.get("reason"):
        details.append(f"原因={payload.get('reason')}")
    suffix = "；".join(details) if details else "无摘要字段"
    return f"【AIOps Run Trace】{label}：{suffix}"
