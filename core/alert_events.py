"""Persistent alert event store for AIOps workflows."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
ALERT_STORE_PATH = ROOT_DIR / "alert_events.json"
_LOCK = threading.RLock()

ALLOWED_STATUS = {"open", "acknowledged", "closed", "suppressed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_store() -> list[dict[str, Any]]:
    if not ALERT_STORE_PATH.exists():
        return []
    try:
        data = json.loads(ALERT_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _write_store(items: list[dict[str, Any]]) -> None:
    ALERT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_alert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload or {})
    host = (
        payload.get("host")
        or payload.get("node")
        or payload.get("device")
        or payload.get("MonitorName")
        or "all"
    )
    alert_name = (
        payload.get("alert_name")
        or payload.get("displayName")
        or payload.get("name")
        or "System Alert"
    )
    severity = (
        payload.get("severity")
        or payload.get("Severity")
        or payload.get("priority")
        or payload.get("status")
        or "warning"
    )
    description = (
        payload.get("description")
        or payload.get("message")
        or payload.get("Message")
        or payload.get("AlarmMessage")
        or str(payload)
    )
    source = payload.get("source") or payload.get("generatorURL") or payload.get("receiver") or "webhook"
    return {
        "host": str(host),
        "alert_name": str(alert_name),
        "severity": str(severity).lower(),
        "description": str(description),
        "source": str(source),
        "payload": payload,
    }


def create_alert_event(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_alert_payload(payload)
    event = {
        "id": f"alert_{uuid.uuid4().hex[:12]}",
        "created_at": _now(),
        "updated_at": _now(),
        "closed_at": None,
        "status": "open",
        "assignee": "",
        "notes": [],
        **normalized,
    }
    with _LOCK:
        items = _read_store()
        items.insert(0, event)
        _write_store(items[:5000])
    return event


def list_alert_events(
    *,
    status: str | None = None,
    severity: str | None = None,
    host: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    with _LOCK:
        items = _read_store()
    if status:
        items = [item for item in items if item.get("status") == status]
    if severity:
        severity = severity.lower()
        items = [item for item in items if str(item.get("severity", "")).lower() == severity]
    if host:
        host = host.lower()
        items = [item for item in items if host in str(item.get("host", "")).lower()]
    return items[: max(1, min(int(limit or 200), 1000))]


def get_alert_event(alert_id: str) -> dict[str, Any] | None:
    with _LOCK:
        for item in _read_store():
            if item.get("id") == alert_id:
                return item
    return None


def update_alert_event(
    alert_id: str,
    *,
    status: str | None = None,
    assignee: str | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    with _LOCK:
        items = _read_store()
        updated = None
        for item in items:
            if item.get("id") != alert_id:
                continue
            if status:
                status = status.lower()
                if status not in ALLOWED_STATUS:
                    raise ValueError(f"不支持的告警状态: {status}")
                item["status"] = status
                if status == "closed":
                    item["closed_at"] = item.get("closed_at") or _now()
                elif status != "closed":
                    item["closed_at"] = None
            if assignee is not None:
                item["assignee"] = assignee
            if note:
                notes = item.setdefault("notes", [])
                notes.append({"time": _now(), "content": note})
            item["updated_at"] = _now()
            updated = item
            break
        if updated is None:
            return None
        _write_store(items)
        return updated


def alert_summary() -> dict[str, Any]:
    alerts = list_alert_events(limit=5000)
    by_status: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_host: dict[str, int] = {}
    for alert in alerts:
        by_status[alert.get("status", "unknown")] = by_status.get(alert.get("status", "unknown"), 0) + 1
        by_severity[alert.get("severity", "unknown")] = by_severity.get(alert.get("severity", "unknown"), 0) + 1
        host = alert.get("host", "unknown")
        by_host[host] = by_host.get(host, 0) + 1
    return {
        "total": len(alerts),
        "open": by_status.get("open", 0),
        "by_status": by_status,
        "by_severity": by_severity,
        "top_hosts": sorted(by_host.items(), key=lambda item: item[1], reverse=True)[:10],
    }
