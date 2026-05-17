"""Persistent approval queue and audit trail for high-risk tool calls."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from core.redaction import redact_json_text, redact_value
from core.skill_lifecycle import validate_skill_candidate
from core.tool_trace_policy import (
    trace_command_action_summary,
    trace_http_action_summary,
    trace_sql_action_summary,
)


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
    allow_modifications = context.get("allow_modifications")
    session_mode = context.get("session_mode")
    normalized_allow_modifications = None
    if isinstance(allow_modifications, bool):
        normalized_allow_modifications = allow_modifications
    elif isinstance(allow_modifications, (int, float)):
        normalized_allow_modifications = bool(allow_modifications)
    elif isinstance(allow_modifications, str):
        value = allow_modifications.strip().lower()
        if value in {"true", "1", "yes", "on", "rw", "readwrite", "r+w", "write"}:
            normalized_allow_modifications = True
        elif value in {"false", "0", "no", "off", "ro", "readonly"}:
            normalized_allow_modifications = False
    safe_context = {
        "session_id": context.get("session_id"),
        "host": context.get("host"),
        "port": context.get("port"),
        "username": context.get("username"),
        "asset_type": context.get("asset_type"),
        "protocol": context.get("protocol"),
        "remark": context.get("remark"),
        "target_scope": context.get("target_scope"),
        "scope_value": context.get("scope_value"),
        "execution_mode": context.get("execution_mode"),
        "trigger_source": context.get("trigger_source"),
        "tags": context.get("tags") or [],
    }
    if session_mode is not None:
        if isinstance(session_mode, bool):
            safe_context["session_mode"] = "readwrite" if session_mode else "readonly"
        elif isinstance(session_mode, str) and session_mode.strip():
            safe_context["session_mode"] = session_mode.strip().lower()
    elif normalized_allow_modifications is not None:
        safe_context["session_mode"] = "readwrite" if normalized_allow_modifications else "readonly"
    if normalized_allow_modifications is not None:
        safe_context["allow_modifications"] = normalized_allow_modifications
    return redact_value(
        safe_context
    )


def _preview_text(value: str, limit: int = 800) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...<truncated {len(text) - limit} chars>"


def _skill_change_metadata(args: dict[str, Any]) -> dict[str, Any]:
    content = str((args or {}).get("content") or "")
    validation = validate_skill_candidate(
        str((args or {}).get("skill_id") or ""),
        str((args or {}).get("file_name") or ""),
        content,
    )
    return {
        "type": "skill_change",
        "skill_id": validation["skill_id"],
        "file_name": validation["file_name"],
        "content_chars": len(content),
        "content_lines": len(content.splitlines()),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_preview": _preview_text(content),
        "validation": {
            "valid": validation["valid"],
            "issues": validation["issues"],
            "warnings": validation["warnings"],
        },
    }


def _skill_rollback_metadata(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "skill_rollback",
        "skill_id": str((args or {}).get("skill_id") or "").strip(),
        "file_name": str((args or {}).get("file_name") or "").strip(),
        "version_id": str((args or {}).get("version_id") or "").strip(),
        "target_file": redact_value(str((args or {}).get("target_file") or "")),
        "version_file": redact_value(str((args or {}).get("version_file") or "")),
    }


def _policy_metadata(tool_name: str, args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.safety_policy import explain_policy_decision

        result = explain_policy_decision(tool_name, args or {}, context or {})
    except Exception:
        return {}
    actions = result.get("actions") if isinstance(result, dict) else None
    primary_action = result.get("primary_action") if isinstance(result, dict) else None
    metadata: dict[str, Any] = {}
    if isinstance(actions, list) and actions:
        metadata["actions"] = redact_value(actions)
    if isinstance(primary_action, dict):
        metadata["primary_action"] = redact_value(primary_action)
    return metadata


def _requested_action_metadata(
    tool_name: str,
    args: dict[str, Any],
    tool_policy: dict[str, Any] | None,
) -> dict[str, str]:
    payload_args: Any = args or {}
    result_meta: dict[str, Any] = {"tool_policy": tool_policy or {}}
    if tool_name == "db_execute_query" and isinstance(args, dict):
        payload_args = args.get("sql") or args
    elif isinstance(args, dict) and args.get("method"):
        result_meta["method"] = args.get("method")
    trace = {
        "tool": tool_name,
        "args": payload_args,
        "resultMeta": result_meta,
    }
    for kind, summary in (
        ("sql", trace_sql_action_summary(trace)),
        ("http", trace_http_action_summary(trace)),
        ("command", trace_command_action_summary(trace)),
    ):
        if summary:
            return {"kind": kind, "label": summary}
    return {}


def _approval_source_metadata(
    *,
    reason: str,
    tool_policy: dict[str, Any] | None,
    policy: dict[str, Any],
    approval_sources: tuple[str, ...] | list[str] | None = None,
) -> list[dict[str, str]]:
    policy = policy or {}
    requested_layers = [
        str(item)
        for item in (approval_sources or [])
        if str(item) in {"runtime_policy", "safety_policy", "action_policy"}
    ]
    requested_layers = list(dict.fromkeys(requested_layers))

    if not requested_layers:
        if isinstance(policy.get("primary_action"), dict):
            requested_layers.append("action_policy")
        else:
            tool_policy = tool_policy or {}
            operation_mode = str(tool_policy.get("operation_mode") or "")
            approval_policy = str(tool_policy.get("approval_policy") or "")
            destructive = bool(tool_policy.get("destructive"))
            if (
                str(reason or "").startswith("工具执行策略要求审批")
                or destructive
                or approval_policy == "always_required"
                or operation_mode == "external_effect"
            ):
                requested_layers.append("runtime_policy")
            else:
                requested_layers.append("safety_policy")

    sources: list[dict[str, str]] = []

    if "runtime_policy" in requested_layers:
        tool_policy = tool_policy or {}
        operation_mode = str(tool_policy.get("operation_mode") or "")
        approval_policy = str(tool_policy.get("approval_policy") or "")
        destructive = bool(tool_policy.get("destructive"))
        runtime_detail = f"模式={operation_mode or 'unknown'}，审批={approval_policy or 'unknown'}"
        if destructive:
            runtime_detail = f"{runtime_detail}（含写操作/高危特征）"
        sources.append(
            {
                "layer": "runtime_policy",
                "label": "运行策略",
                "detail": runtime_detail,
                "reason": str(reason or ""),
            }
        )

    if "safety_policy" in requested_layers:
        sources.append(
            {
                "layer": "safety_policy",
                "label": "安全策略",
                "detail": "命中安全审批规则或只读边界",
                "reason": str(reason or ""),
            }
        )

    if "action_policy" in requested_layers:
        action = policy.get("primary_action") if isinstance(policy, dict) else None
        if isinstance(action, dict):
            sources.append(
                {
                    "layer": "action_policy",
                    "label": "动作策略",
                    "detail": str(action.get("label") or action.get("id") or "命中动作审批规则"),
                    "reason": str(reason or ""),
                }
            )
        elif not any(item.get("layer") == "action_policy" for item in sources):
            sources.append(
                {
                    "layer": "action_policy",
                    "label": "动作策略",
                    "detail": "命中动作审批规则",
                    "reason": str(reason or ""),
                }
            )

    if not sources:
        sources.append(
            {
                "layer": "safety_policy",
                "label": "安全策略",
                "detail": "命中安全审批规则或只读边界",
                "reason": str(reason or ""),
            }
        )
    return sources


def _approval_metadata(
    tool_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    reason: str,
    approval_sources: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    tool_policy: dict[str, Any] | None = None
    try:
        from core.tool_registry import tool_policy_metadata

        tool_policy = tool_policy_metadata(tool_name)
        metadata["tool_policy"] = redact_value(tool_policy)
    except Exception:
        pass
    policy = _policy_metadata(tool_name, args, context)
    if policy:
        metadata["policy"] = policy
    requested_action = _requested_action_metadata(tool_name, args, tool_policy)
    if requested_action:
        metadata["requested_action"] = redact_value(requested_action)
    metadata["approval_sources"] = redact_value(
        _approval_source_metadata(
            reason=reason,
            tool_policy=tool_policy,
            policy=policy,
            approval_sources=approval_sources,
        )
    )
    metadata["approval_source"] = metadata["approval_sources"][0] if metadata["approval_sources"] else None
    if tool_name == "evolve_skill":
        metadata["skill_change"] = _skill_change_metadata(args)
    elif tool_name == "rollback_skill":
        metadata["skill_rollback"] = _skill_rollback_metadata(args)
    return metadata


def _tool_result_success(result: str) -> bool:
    try:
        parsed = json.loads(result)
    except Exception:
        return True
    if not isinstance(parsed, dict):
        return True
    status = str(parsed.get("status") or "").upper()
    if status in {"ERROR", "FAILED", "BLOCKED"}:
        return False
    if parsed.get("success") is False or parsed.get("has_error") is True:
        return False
    if parsed.get("error") or parsed.get("reason"):
        return False
    return True


def _execution_artifacts(result: str) -> dict[str, Any]:
    try:
        parsed = json.loads(result)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    artifacts = {}
    for key in ("skill_id", "file_name", "file_path", "backup_path", "version_id", "restored_version_path"):
        value = parsed.get(key)
        if value is not None:
            artifacts[key] = redact_value(value)
    return artifacts


def _execution_metadata(result: str) -> dict[str, Any]:
    try:
        parsed = json.loads(result)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    metadata: dict[str, Any] = {}
    for key in ("statement_type", "has_result_set", "committed", "affected_rows", "count", "message"):
        value = parsed.get(key)
        if value is not None:
            metadata[key] = redact_value(value)
    if metadata:
        metadata["type"] = "database_statement"
    return metadata


def _safe_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    safe_args = redact_value(args or {})
    if tool_name == "evolve_skill" and isinstance(safe_args, dict) and "content" in safe_args:
        content = str((args or {}).get("content") or "")
        safe_args["content"] = {
            "preview": _preview_text(content, limit=240),
            "chars": len(content),
            "lines": len(content.splitlines()),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
    return safe_args


def _execution_summary(tool_result: Any) -> dict[str, Any]:
    text = redact_json_text(str(tool_result or ""))
    summary = {
        "status": "success" if _tool_result_success(text) else "error",
        "result_chars": len(text),
        "result_preview": _preview_text(text, limit=800),
        "completed_at": _iso(),
        "completed_at_ts": _now(),
    }
    artifacts = _execution_artifacts(text)
    if artifacts:
        summary["artifacts"] = artifacts
    metadata = _execution_metadata(text)
    if metadata:
        summary["metadata"] = metadata
    return summary


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
    approval_sources: tuple[str, ...] | list[str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    now = _now()
    approval_id = str(tool_call_id or "").strip()
    if not approval_id:
        raise ValueError("approval id 不能为空")
    timeout = max(30, min(int(timeout_seconds or 300), 1800))
    with _LOCK:
        items = _read_store()
        changed = _expire_pending(items)
        if any(existing.get("id") == approval_id for existing in items):
            if changed:
                _write_store(items)
            raise ValueError("审批请求 ID 已存在，不能复用")

        item = {
            "id": approval_id,
            "tool_call_id": approval_id,
            "session_id": str(session_id or context.get("session_id") or ""),
            "tool_name": str(tool_name or ""),
            "args": _safe_args(str(tool_name or ""), args or {}),
            "reason": str(reason or ""),
            "metadata": _approval_metadata(
                str(tool_name or ""),
                args or {},
                context or {},
                str(reason or ""),
                approval_sources=approval_sources,
            ),
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
        items.append(item)
        _write_store(sorted(items, key=lambda value: value.get("requested_at_ts", 0), reverse=True))
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


def _approval_layers(item: dict[str, Any]) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    sources = metadata.get("approval_sources") if isinstance(metadata, dict) else None
    layers: list[str] = []
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict):
                layer = str(source.get("layer") or "").strip()
                if layer:
                    layers.append(layer)
    if not layers and isinstance(metadata, dict):
        source = metadata.get("approval_source")
        if isinstance(source, dict):
            layer = str(source.get("layer") or "").strip()
            if layer:
                layers.append(layer)
    return list(dict.fromkeys(layers or ["unknown"]))


def _approval_risks(item: dict[str, Any]) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    tool_policy = metadata.get("tool_policy") if isinstance(metadata, dict) else {}
    if not isinstance(tool_policy, dict):
        tool_policy = {}
    operation_mode = str(tool_policy.get("operation_mode") or "").strip()
    approval_policy = str(tool_policy.get("approval_policy") or "").strip()
    risks: list[str] = []
    if bool(tool_policy.get("destructive")) or operation_mode == "destructive":
        risks.append("destructive")
    if operation_mode in {"write", "read_write", "external_effect"} or approval_policy == "guarded_write":
        risks.append("write_or_external")
    if isinstance(metadata, dict) and (metadata.get("skill_change") or metadata.get("skill_rollback")):
        risks.append("skill_change")
    return list(dict.fromkeys(risks or ["policy_only"]))


def approval_audit_summary(limit: int = 500) -> dict[str, Any]:
    with _LOCK:
        items = _read_store()
        changed = _expire_pending(items)
        if changed:
            _write_store(items)
    try:
        safe_limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        safe_limit = 500
    approvals = sorted(items, key=lambda value: value.get("requested_at_ts", 0), reverse=True)[:safe_limit]
    by_status = {"pending": 0, "approved": 0, "rejected": 0, "timeout": 0}
    by_tool: dict[str, int] = {}
    by_layer: dict[str, int] = {}
    by_risk = {"destructive": 0, "write_or_external": 0, "skill_change": 0, "policy_only": 0}
    for item in approvals:
        status = str(item.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        tool_name = str(item.get("tool_name") or "unknown")
        by_tool[tool_name] = by_tool.get(tool_name, 0) + 1
        for layer in _approval_layers(item):
            by_layer[layer] = by_layer.get(layer, 0) + 1
        for risk in _approval_risks(item):
            by_risk[risk] = by_risk.get(risk, 0) + 1
    recent = [
        {
            "id": item.get("id"),
            "status": item.get("status"),
            "tool_name": item.get("tool_name"),
            "session_id": item.get("session_id"),
            "reason": item.get("reason"),
            "requested_at": item.get("requested_at"),
            "resolved_at": item.get("resolved_at"),
        }
        for item in approvals[:8]
    ]
    return {
        "total": len(approvals),
        "limit": safe_limit,
        "by_status": by_status,
        "by_tool": by_tool,
        "by_layer": by_layer,
        "by_risk": by_risk,
        "recent": recent,
    }


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


def record_approval_execution(approval_id: str, tool_result: Any) -> dict[str, Any]:
    execution = _execution_summary(tool_result)
    with _LOCK:
        items = _read_store()
        for item in items:
            if item.get("id") != approval_id:
                continue
            if item.get("execution"):
                raise ValueError("审批执行结果已存在，不能覆盖")
            item["execution"] = execution
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
