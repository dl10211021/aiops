"""Persistent alert event store for AIOps workflows."""

from __future__ import annotations

import json
import threading
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.alert_policy import build_alert_policy


ROOT_DIR = Path(__file__).resolve().parent.parent
ALERT_STORE_PATH = ROOT_DIR / "alert_events.json"
_LOCK = threading.RLock()
_STORE_CACHE: tuple[str, float, int, list[dict[str, Any]]] | None = None

ALLOWED_STATUS = {"open", "acknowledged", "closed", "suppressed"}
RECOVERY_STATUSES = {"resolved", "ok", "closed", "recovered", "recovery"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_store() -> list[dict[str, Any]]:
    global _STORE_CACHE
    if not ALERT_STORE_PATH.exists():
        _STORE_CACHE = None
        return []
    try:
        stat = ALERT_STORE_PATH.stat()
        cache_path = str(ALERT_STORE_PATH)
        if _STORE_CACHE and _STORE_CACHE[0] == cache_path and _STORE_CACHE[1] == stat.st_mtime and _STORE_CACHE[2] == stat.st_size:
            return [dict(item) for item in _STORE_CACHE[3]]
    except OSError:
        return []
    try:
        data = json.loads(ALERT_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    items = [item for item in data if isinstance(item, dict)]
    try:
        stat = ALERT_STORE_PATH.stat()
        _STORE_CACHE = (str(ALERT_STORE_PATH), stat.st_mtime, stat.st_size, [dict(item) for item in items])
    except OSError:
        _STORE_CACHE = None
    return items


def _write_store(items: list[dict[str, Any]]) -> None:
    global _STORE_CACHE
    ALERT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _STORE_CACHE = None


def _compact_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _first_value(mapping: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return _compact_str(value, default)
    return default


def _severity_from_status(status: Any, default: str = "warning") -> str:
    value = _compact_str(status, default).lower()
    if value in RECOVERY_STATUSES:
        return "info"
    return value


def _fingerprint(*parts: Any) -> str:
    text = "|".join(_compact_str(part) for part in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _host_from_labels(labels: dict[str, Any]) -> str:
    return _first_value(
        labels,
        "host",
        "instance",
        "node",
        "device",
        "hostname",
        "server",
        default="all",
    )


def _normalize_alertmanager_alert(alert: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    labels = alert.get("labels") if isinstance(alert.get("labels"), dict) else {}
    annotations = alert.get("annotations") if isinstance(alert.get("annotations"), dict) else {}
    status = _first_value(alert, "status", default=_first_value(envelope, "status", default="firing"))
    host = _host_from_labels(labels)
    alert_name = _first_value(labels, "alertname", "name", default="Alertmanager Alert")
    severity = _first_value(labels, "severity", "priority", default=_severity_from_status(status))
    description = _first_value(
        annotations,
        "description",
        "message",
        "summary",
        default=_first_value(alert, "generatorURL", default=str(alert)),
    )
    external_id = _first_value(alert, "fingerprint", default="")
    fingerprint = external_id or _fingerprint("alertmanager", host, alert_name, labels.get("severity"), labels.get("job"))
    return {
        "host": host,
        "alert_name": alert_name,
        "severity": severity.lower(),
        "description": description,
        "source": _first_value(envelope, "receiver", default="alertmanager"),
        "source_type": "alertmanager",
        "external_id": external_id,
        "fingerprint": fingerprint,
        "starts_at": _first_value(alert, "startsAt", "starts_at"),
        "ends_at": _first_value(alert, "endsAt", "ends_at"),
        "labels": labels,
        "annotations": annotations,
        "payload": alert,
        "status_hint": status.lower(),
    }


def expand_alert_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = dict(payload or {})
    alerts = payload.get("alerts")
    if isinstance(alerts, list):
        expanded = [
            _normalize_alertmanager_alert(alert, payload)
            for alert in alerts
            if isinstance(alert, dict)
        ]
        if expanded:
            return expanded
    return [normalize_alert_payload(payload)]


def normalize_alert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload or {})
    source_type = _first_value(payload, "source_type", "source", "receiver", default="webhook").lower()
    labels = payload.get("labels") if isinstance(payload.get("labels"), dict) else {}
    annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
    host = (
        payload.get("host")
        or payload.get("node")
        or payload.get("device")
        or payload.get("MonitorName")
        or payload.get("resource")
        or payload.get("ip")
        or payload.get("hostname")
        or _host_from_labels(labels)
        or "all"
    )
    alert_name = (
        payload.get("alert_name")
        or payload.get("displayName")
        or payload.get("name")
        or payload.get("trigger_name")
        or payload.get("event_name")
        or payload.get("alarmName")
        or payload.get("AlarmName")
        or labels.get("alertname")
        or "System Alert"
    )
    severity = (
        payload.get("severity")
        or payload.get("Severity")
        or payload.get("priority")
        or payload.get("status")
        or labels.get("severity")
        or "warning"
    )
    description = (
        payload.get("description")
        or payload.get("message")
        or payload.get("Message")
        or payload.get("AlarmMessage")
        or payload.get("summary")
        or annotations.get("description")
        or annotations.get("summary")
        or str(payload)
    )
    source = payload.get("source") or payload.get("generatorURL") or payload.get("receiver") or source_type or "webhook"
    external_id = _first_value(payload, "external_id", "event_id", "eventid", "triggerid", "fingerprint", "id")
    status_hint = _first_value(payload, "status", "event_status", "state", default="").lower()
    fingerprint = (
        _first_value(payload, "fingerprint")
        or _fingerprint(source_type, host, alert_name, external_id or payload.get("objectid") or "")
    )
    return {
        "host": str(host),
        "alert_name": str(alert_name),
        "severity": str(severity).lower(),
        "description": str(description),
        "source": str(source),
        "source_type": str(source_type),
        "external_id": external_id,
        "fingerprint": fingerprint,
        "starts_at": _first_value(payload, "starts_at", "startsAt", "event_time", "clock", "created_at"),
        "ends_at": _first_value(payload, "ends_at", "endsAt", "resolved_at", "recovery_time"),
        "labels": labels,
        "annotations": annotations,
        "payload": payload,
        "status_hint": status_hint,
    }


def _is_recovery_event(normalized: dict[str, Any]) -> bool:
    status_hint = _compact_str(normalized.get("status_hint")).lower()
    return bool(normalized.get("ends_at")) or status_hint in RECOVERY_STATUSES


def _merge_alert_event(items: list[dict[str, Any]], normalized: dict[str, Any]) -> dict[str, Any] | None:
    fingerprint = normalized.get("fingerprint")
    if not fingerprint:
        return None
    for item in items:
        if item.get("fingerprint") == fingerprint and item.get("status") in {"open", "acknowledged"}:
            repeat_count = int(item.get("repeat_count") or 1) + 1
            item.update(
                {
                    "updated_at": _now(),
                    "host": normalized["host"],
                    "alert_name": normalized["alert_name"],
                    "severity": normalized["severity"],
                    "description": normalized["description"],
                    "source": normalized["source"],
                    "source_type": normalized["source_type"],
                    "external_id": normalized.get("external_id", ""),
                    "starts_at": normalized.get("starts_at", item.get("starts_at", "")),
                    "ends_at": normalized.get("ends_at", item.get("ends_at", "")),
                    "labels": normalized.get("labels", {}),
                    "annotations": normalized.get("annotations", {}),
                    "payload": normalized.get("payload", {}),
                    "repeat_count": repeat_count,
                }
            )
            if _is_recovery_event(normalized):
                item["status"] = "closed"
                item["closed_at"] = item.get("closed_at") or _now()
            item.update(build_alert_policy(item))
            return item
    return None


def create_alert_event(payload: dict[str, Any]) -> dict[str, Any]:
    if all(key in payload for key in ("host", "alert_name", "severity", "description", "source_type", "fingerprint")):
        normalized = dict(payload)
    else:
        normalized = normalize_alert_payload(payload)
    event = {
        "id": f"alert_{uuid.uuid4().hex[:12]}",
        "created_at": _now(),
        "updated_at": _now(),
        "closed_at": None,
        "status": "closed" if _is_recovery_event(normalized) else "open",
        "assignee": "",
        "notes": [],
        "repeat_count": 1,
        **normalized,
    }
    if event["status"] == "closed":
        event["closed_at"] = _now()
    event.update(build_alert_policy(event))
    with _LOCK:
        items = _read_store()
        merged = _merge_alert_event(items, normalized)
        if merged:
            _write_store(items[:5000])
            return merged
        items.insert(0, event)
        _write_store(items[:5000])
    return event


def create_alert_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [create_alert_event(item) for item in expand_alert_payload(payload)]


def list_alert_events(
    *,
    status: str | None = None,
    severity: str | None = None,
    host: str | None = None,
    source_family: str | None = None,
    automation_mode: str | None = None,
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
    if source_family:
        source_family = source_family.lower()
        items = [
            item
            for item in items
            if str(item.get("source_family") or item.get("source_type") or item.get("source") or "").lower() == source_family
        ]
    if automation_mode:
        automation_mode = automation_mode.lower()
        if automation_mode in {"ai", "run_ai"}:
            items = [item for item in items if bool((item.get("automation_decision") or {}).get("run_ai"))]
        elif automation_mode in {"record_only", "record"}:
            items = [item for item in items if not bool((item.get("automation_decision") or {}).get("run_ai"))]
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
