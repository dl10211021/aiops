from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from core.redaction import redact_value
from core.run_hooks import register_run_hook

RUN_TRACE_MEMORY_TYPE = "aiops_run_trace"


def build_run_trace_message(event_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    session_id = str((payload or {}).get("session_id") or "").strip()
    if not session_id:
        return None
    safe_payload = redact_value(payload or {})
    return {
        "role": "system",
        "content": _run_trace_content(event_type, safe_payload),
        "memory_type": RUN_TRACE_MEMORY_TYPE,
        "visible_to_user": False,
        "run_event_type": event_type,
        "run_event_payload": safe_payload,
        "run_event_ts": time.time(),
    }


def register_session_run_trace_hooks(memory_store: Any) -> Callable[[], None]:
    def handler(event_type: str, payload: dict[str, Any]) -> None:
        event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        message = build_run_trace_message(event_type, event_payload)
        if not message:
            return
        memory_store.append_message(message["run_event_payload"]["session_id"], message)

    unregister_all = register_run_hook("*", handler)
    return unregister_all


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
