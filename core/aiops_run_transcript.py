from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()
_SAFE_RUN_ID_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")
_MAX_MESSAGE_CHARS = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_run_id(run_id: str) -> str:
    clean = _SAFE_RUN_ID_RE.sub("-", str(run_id or "").strip()).strip("-")
    return clean[:160] or "unknown"


def _event_path(root: Path, run_id: str) -> Path:
    return root / f"{_safe_run_id(run_id)}.jsonl"


def _compact(value: Any) -> Any:
    if isinstance(value, str):
        return value[:_MAX_MESSAGE_CHARS]
    if isinstance(value, list):
        return [_compact(item) for item in value[:200]]
    if isinstance(value, dict):
        return {str(key): _compact(item) for key, item in value.items()}
    return value


def append_run_event(
    *,
    root: Path,
    run_id: str,
    event_type: str,
    message: str,
    status: str | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "opscore",
    event_time: str | None = None,
) -> dict[str, Any]:
    event = {
        "id": f"evt_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
        "run_id": str(run_id),
        "time": event_time or _now(),
        "type": str(event_type or "event"),
        "source": str(source or "opscore"),
        "message": str(message or "")[:_MAX_MESSAGE_CHARS],
    }
    if status:
        event["status"] = str(status)
    if payload:
        event["payload"] = _compact(payload)

    root.mkdir(parents=True, exist_ok=True)
    path = _event_path(root, run_id)
    line = json.dumps(event, ensure_ascii=False, default=str)
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
    return event


def read_run_events(
    *,
    root: Path,
    run_id: str,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    path = _event_path(root, run_id)
    if not path.exists():
        return []
    safe_limit = max(1, min(int(limit or 1000), 5000))
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    events.append(item)
    except OSError:
        return []
    return events[-safe_limit:]


def delete_run_events(*, root: Path, run_id: str) -> bool:
    path = _event_path(root, run_id)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
