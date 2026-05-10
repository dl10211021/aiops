from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def _timestamp_ms(now: Callable[[], float]) -> int:
    return int(now() * 1000)


def append_tool_trace_event(
    exec_trace: list[dict[str, Any]],
    event: dict[str, Any],
    *,
    now: Callable[[], float] = time.time,
) -> None:
    event_type = event.get("type")
    now_ms = _timestamp_ms(now)
    if event_type == "tool_start":
        exec_trace.append(
            {
                "type": "tool_start",
                "tool": str(event.get("tool") or "unknown"),
                "args": str(event.get("args") or ""),
                "status": "running",
                "startedAt": event.get("startedAt") or now_ms,
            }
        )
        return
    if event_type != "tool_end":
        return

    completed = {
        "type": "tool_end",
        "tool": str(event.get("tool") or "unknown"),
        "result": str(event.get("result") or ""),
        "resultMeta": event.get("resultMeta") or {},
        "evidenceId": str(event.get("evidenceId") or ""),
        "evidence": event.get("evidence") or {},
        "status": event.get("status") if event.get("status") in {"done", "error"} else "done",
        "completedAt": event.get("completedAt") or now_ms,
    }
    for index in range(len(exec_trace) - 1, -1, -1):
        item = exec_trace[index]
        if item.get("type") == "tool_start" and item.get("status") == "running":
            exec_trace[index] = {**item, **completed}
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
