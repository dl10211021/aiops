from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _elapsed_ms(started_at: str | None, ended_at: str | None = None) -> int:
    start = _parse_time(started_at)
    if not start:
        return 0
    end = _parse_time(ended_at) or datetime.now(timezone.utc)
    return max(0, int((end - start).total_seconds() * 1000))


def _target_ref(target: dict[str, Any] | None) -> dict[str, Any] | None:
    if not target:
        return None
    return {
        "asset_id": target.get("asset_id"),
        "host": target.get("host"),
        "asset_type": target.get("asset_type"),
        "protocol": target.get("protocol"),
    }


@dataclass
class AIOpsTaskRuntime:
    task_id: str
    owner_id: str
    run_id: str
    task: Any
    started_at: str
    task_type: str = "inspection"
    status: str = "running"
    current_stage: str = "starting"
    message: str = ""
    progress_current: int = 0
    progress_total: int = 0
    current_target: dict[str, Any] | None = None
    cancel_requested_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_progress(
        self,
        *,
        stage: str,
        message: str = "",
        current: int | None = None,
        total: int | None = None,
        target: dict[str, Any] | None = None,
        status: str = "running",
    ) -> None:
        self.status = status
        self.current_stage = stage
        if message:
            self.message = message
        if current is not None:
            self.progress_current = max(0, int(current))
        if total is not None:
            self.progress_total = max(0, int(total))
        if target is not None:
            self.current_target = _target_ref(target)

    def request_cancel(self, message: str = "任务正在取消。") -> None:
        self.status = "cancelling"
        self.current_stage = "cancelling"
        self.message = message
        self.cancel_requested_at = self.cancel_requested_at or _now()

    def mark_finished(self, status: str, message: str = "") -> None:
        self.status = status
        self.current_stage = "finished"
        if message:
            self.message = message
        self.completed_at = self.completed_at or _now()

    def snapshot(self) -> dict[str, Any]:
        task_done = bool(self.task is not None and self.task.done())
        total = max(0, int(self.progress_total or 0))
        current = max(0, int(self.progress_current or 0))
        percent = int(round((current / total) * 100)) if total else 0
        if self.status in {"completed", "failed", "cancelled"}:
            percent = 100
        return {
            "task_id": self.task_id,
            "owner_id": self.owner_id,
            "run_id": self.run_id,
            "task_type": self.task_type,
            "task": self.task,
            "status": self.status,
            "running": not task_done and self.status in {"running", "cancelling"},
            "current_stage": self.current_stage,
            "message": self.message,
            "progress_current": current,
            "progress_total": total,
            "progress_percent": max(0, min(100, percent)),
            "current_target": self.current_target,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_ms": _elapsed_ms(self.started_at, self.completed_at),
            "cancel_requested_at": self.cancel_requested_at,
            "metadata": dict(self.metadata),
        }


def task_runtime_snapshot(value: Any) -> dict[str, Any]:
    if isinstance(value, AIOpsTaskRuntime):
        return value.snapshot()
    if isinstance(value, dict):
        return dict(value)
    return {}
