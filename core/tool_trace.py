from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def _timestamp_ms(now: Callable[[], float]) -> int:
    return int(now() * 1000)


def _merge_result_meta(
    start_meta: dict[str, Any] | None,
    end_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(start_meta, dict):
        merged.update(start_meta)
    if isinstance(end_meta, dict):
        merged.update(end_meta)
    return merged


def _trace_call_id(event: dict[str, Any]) -> str:
    return str(
        event.get("toolCallId")
        or event.get("tool_call_id")
        or event.get("id")
        or ""
    )


def append_tool_trace_event(
    exec_trace: list[dict[str, Any]],
    event: dict[str, Any],
    *,
    now: Callable[[], float] = time.time,
) -> None:
    event_type = event.get("type")
    now_ms = _timestamp_ms(now)
    if event_type == "tool_start":
        tool_call_id = _trace_call_id(event)
        exec_trace.append(
            {
                "type": "tool_start",
                "toolCallId": tool_call_id,
                "tool": str(event.get("tool") or "unknown"),
                "args": str(event.get("args") or ""),
                "resultMeta": event.get("resultMeta") or {},
                "status": "running",
                "startedAt": event.get("startedAt") or now_ms,
            }
        )
        return
    if event_type != "tool_end":
        return

    result_meta = event.get("resultMeta") if isinstance(event.get("resultMeta"), dict) else {}
    tool_call_id = _trace_call_id(event)
    completed = {
        "type": "tool_end",
        "toolCallId": tool_call_id,
        "tool": str(event.get("tool") or "unknown"),
        "result": str(event.get("result") or ""),
        "resultMeta": result_meta,
        "evidenceId": str(event.get("evidenceId") or ""),
        "evidence": event.get("evidence") or {},
        "status": event.get("status") if event.get("status") in {"done", "error"} else "done",
        "completedAt": event.get("completedAt") or now_ms,
    }
    for index in range(len(exec_trace) - 1, -1, -1):
        item = exec_trace[index]
        if item.get("type") != "tool_start" or item.get("status") != "running":
            continue
        item_call_id = str(item.get("toolCallId") or "")
        if tool_call_id and item_call_id and item_call_id != tool_call_id:
            continue
        exec_trace[index] = {
            **item,
            **completed,
            "resultMeta": _merge_result_meta(item.get("resultMeta"), result_meta),
        }
        return
    exec_trace.append(completed)


def make_tool_trace_collector(
    exec_trace: list[dict[str, Any]],
    *,
    now: Callable[[], float] = time.time,
) -> Callable[[dict[str, Any]], None]:
    def collect(event: dict[str, Any]) -> None:
        append_tool_trace_event(exec_trace, event, now=now)

    return collect
