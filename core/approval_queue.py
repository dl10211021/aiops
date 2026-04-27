"""Persistent approval queue and audit trail for high-risk tool calls."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from core.redaction import redact_value


ROOT_DIR = Path(__file__).resolve().parent.parent
APPROVAL_STORE_PATH = ROOT_DIR / "approval_requests.json"

_LOCK = threading.RLock()

FINAL_STATUSES = {"approved", "rejected", "timeout"}


def _now() -> float:
    return time.time()


def _iso(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_now() if ts is None else ts))


def _read_store() -> list[dict[str, Any]]:
    if not APPROVAL_STORE_PATH.exists():
        return []
    try:
        data = json.loads(APPROVAL_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _write_store(items: list[dict[str, Any]]) -> None:
    APPROVAL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVAL_STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _safe_context(context: dict[str, Any]) -> dict[str, Any]:
    return redact_value(
        {
            "session_id": context.get("session_id"),
            "host": context.get("host"),
            "port": context.get("port"),
            "username": context.get("username"),
            "asset_type": context.get("asset_type"),
            "protocol": context.get("protocol"),
            "remark": context.get("remark"),
            "allow_modifications": bool(context.get("allow_modifications", False)),
            "target_scope": context.get("target_scope"),
            "scope_value": context.get("scope_value"),
            "tags": context.get("tags") or [],
        }
    )


def _expire_pending(items: list[dict[str, Any]]) -> bool:
    changed = False
    now = _now()
    for item in items:
        if item.get("status") != "pending":
            continue
        expires_at = item.get("expires_at_ts")
        if isinstance(expires_at, (int, float)) and expires_at <= now:
            item["status"] = "timeout"
            item["decision"] = "timeout"
            item["resolved_at"] = _iso(now)
            item["resolved_at_ts"] = now
            item["operator"] = "system"
            changed = True
    return changed


def record_approval_request(
    *,
    tool_call_id: str,
    session_id: str,
    tool_name: str,
    args: dict[str, Any],
    reason: str,
    context: dict[str, Any],
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    now = _now()
    approval_id = str(tool_call_id or "").strip()
    if not approval_id:
        raise ValueError("approval id 不能为空")
    timeout = max(30, min(int(timeout_seconds or 300), 1800))
    item = {
        "id": approval_id,
        "tool_call_id": approval_id,
        "session_id": str(session_id or context.get("session_id") or ""),
        "tool_name": str(tool_name or ""),
        "args": redact_value(args or {}),
        "reason": str(reason or ""),
        "context": _safe_context({**(context or {}), "session_id": session_id or context.get("session_id")}),
        "status": "pending",
        "decision": None,
        "operator": None,
        "note": "",
        "requested_at": _iso(now),
        "requested_at_ts": now,
        "expires_at": _iso(now + timeout),
        "expires_at_ts": now + timeout,
        "resolved_at": None,
        "resolved_at_ts": None,
    }
    with _LOCK:
        items = _read_store()
        next_items = [existing for existing in items if existing.get("id") != approval_id]
        next_items.append(item)
        _write_store(sorted(next_items, key=lambda value: value.get("requested_at_ts", 0), reverse=True))
    return item


def get_approval_request(approval_id: str) -> dict[str, Any] | None:
    with _LOCK:
        items = _read_store()
        changed = _expire_pending(items)
        if changed:
            _write_store(items)
        for item in items:
            if item.get("id") == approval_id:
                return item
    return None


def list_approval_requests(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    normalized_status = str(status or "").strip().lower()
    with _LOCK:
        items = _read_store()
        changed = _expire_pending(items)
        if changed:
            _write_store(items)
    if normalized_status:
        items = [item for item in items if item.get("status") == normalized_status]
    try:
        safe_limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        safe_limit = 100
    return sorted(items, key=lambda value: value.get("requested_at_ts", 0), reverse=True)[:safe_limit]


def resolve_approval_request(
    approval_id: str,
    *,
    approved: bool,
    operator: str = "user",
    note: str = "",
) -> dict[str, Any]:
    decision = "approved" if approved else "rejected"
    now = _now()
    with _LOCK:
        items = _read_store()
        _expire_pending(items)
        for item in items:
            if item.get("id") != approval_id:
                continue
            if item.get("status") in FINAL_STATUSES:
                return item
            item["status"] = decision
            item["decision"] = decision
            item["operator"] = str(operator or "user")
            item["note"] = str(note or "")
            item["resolved_at"] = _iso(now)
            item["resolved_at_ts"] = now
            _write_store(items)
            return item
    raise KeyError("审批请求不存在")


def mark_approval_timeout(approval_id: str) -> dict[str, Any]:
    now = _now()
    with _LOCK:
        items = _read_store()
        for item in items:
            if item.get("id") != approval_id:
                continue
            if item.get("status") in FINAL_STATUSES:
                return item
            item["status"] = "timeout"
            item["decision"] = "timeout"
            item["operator"] = "system"
            item["note"] = "审批等待超时，系统自动拒绝。"
            item["resolved_at"] = _iso(now)
            item["resolved_at_ts"] = now
            _write_store(items)
            return item
    raise KeyError("审批请求不存在")
