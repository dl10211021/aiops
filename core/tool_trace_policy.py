from __future__ import annotations

import json
import re
from typing import Any

from core.safety_action_catalog import ACTION_PRIORITY, action_detail
from core.safety_action_classifiers import (
    classify_linux_actions,
    classify_memcached_actions,
    classify_mongodb_actions,
    classify_network_actions,
    classify_redis_actions,
    classify_windows_actions,
)
from core.safety_tool_categories import TOOL_CATEGORY
from core.tool_registry import tool_policy_metadata


_SQL_READ_ACTIONS = {"select", "show", "describe", "desc", "explain", "with"}
_SQL_WRITE_ACTIONS = {
    "alter",
    "analyze",
    "call",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "merge",
    "replace",
    "revoke",
    "truncate",
    "update",
}
_HTTP_READ_METHODS = {"GET", "HEAD", "OPTIONS"}
_HTTP_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def trace_result_meta(trace: dict[str, Any]) -> dict[str, Any]:
    result_meta = trace.get("resultMeta") or trace.get("result_meta")
    return result_meta if isinstance(result_meta, dict) else {}


def trace_evidence(trace: dict[str, Any]) -> dict[str, Any]:
    evidence = trace.get("evidence")
    return evidence if isinstance(evidence, dict) else {}


def trace_evidence_id(trace: dict[str, Any]) -> str:
    evidence_id = trace.get("evidenceId") or trace.get("evidence_id")
    if evidence_id:
        return str(evidence_id)
    return str(trace_evidence(trace).get("evidence_id") or "")


def trace_tool_policy(
    trace: dict[str, Any],
    tool_name: str | None = None,
    *,
    fallback_to_registry: bool = True,
) -> dict[str, Any]:
    policy = trace_result_meta(trace).get("tool_policy")
    if isinstance(policy, dict):
        return policy
    evidence_meta = trace_evidence(trace).get("result_meta")
    if isinstance(evidence_meta, dict) and isinstance(evidence_meta.get("tool_policy"), dict):
        return evidence_meta["tool_policy"]
    if not fallback_to_registry:
        return {}
    return tool_policy_metadata(str(tool_name or trace.get("tool") or "unknown"))


def policy_summary(policy: dict[str, Any]) -> str:
    values = [
        str(policy.get("operation_mode") or ""),
        str(policy.get("approval_policy") or ""),
        str(policy.get("evidence_family") or ""),
    ]
    return "/".join(value for value in values if value)


def trace_policy_summary(
    trace: dict[str, Any],
    tool_name: str | None = None,
    *,
    fallback_to_registry: bool = True,
) -> str:
    return policy_summary(
        trace_tool_policy(
            trace,
            tool_name,
            fallback_to_registry=fallback_to_registry,
        )
    )


def trace_sql_action_summary(trace: dict[str, Any]) -> str:
    if str(trace.get("tool") or "") != "db_execute_query":
        return ""
    statement_type = _trace_statement_type(trace)
    if not statement_type:
        return ""
    action = statement_type.lower()
    if action in _SQL_READ_ACTIONS:
        return f"只读查询 ({action.upper()})"
    if action in _SQL_WRITE_ACTIONS:
        return f"写入/DDL ({action.upper()})"
    return f"待识别 ({action.upper()})"


def trace_http_action_summary(trace: dict[str, Any]) -> str:
    if not _is_http_trace(trace):
        return ""
    method = _trace_http_method(trace)
    if not method:
        return ""
    if method in _HTTP_READ_METHODS:
        return f"只读请求 ({method})"
    if method in _HTTP_WRITE_METHODS:
        return f"写入/变更 ({method})"
    return f"待识别 ({method})"


def trace_command_action_summary(trace: dict[str, Any]) -> str:
    action = trace_command_primary_action(trace)
    if not action:
        return ""
    action_id = str(action.get("id") or "")
    label = str(action.get("label") or action_id)
    if not action_id or not label:
        return ""
    return f"{label} ({action_id})"


def trace_command_primary_action(trace: dict[str, Any]) -> dict[str, Any]:
    for payload in (
        trace_result_meta(trace),
        _evidence_result_meta(trace),
        _parsed_result_payload(trace),
    ):
        action = payload.get("primary_action") if isinstance(payload, dict) else None
        normalized = _normalize_action(action)
        if normalized:
            return normalized

    actions = _command_actions_from_trace(trace)
    return actions[0] if actions else {}


def trace_command_actions(trace: dict[str, Any]) -> list[dict[str, Any]]:
    for payload in (
        trace_result_meta(trace),
        _evidence_result_meta(trace),
        _parsed_result_payload(trace),
    ):
        actions = payload.get("actions") if isinstance(payload, dict) else None
        if isinstance(actions, list):
            normalized = [_normalize_action(action) for action in actions]
            return [action for action in normalized if action]
    return _command_actions_from_trace(trace)


def _is_http_trace(trace: dict[str, Any]) -> bool:
    tool = str(trace.get("tool") or "")
    if tool == "db_execute_query":
        return False
    policy = trace_tool_policy(trace, fallback_to_registry=False)
    evidence_family = str(policy.get("evidence_family") or "")
    return (
        evidence_family in {"http_api", "observability"}
        or "_api_" in tool
        or tool.endswith("_request")
        or tool.endswith("_query")
    )


def _trace_http_method(trace: dict[str, Any]) -> str:
    for payload in (
        trace_result_meta(trace),
        _evidence_result_meta(trace),
        _parsed_result_payload(trace),
    ):
        value = payload.get("method") if isinstance(payload, dict) else None
        if value:
            return _normalize_http_method(value)

    for value in (
        trace.get("args"),
        trace_evidence(trace).get("input_summary"),
        trace_evidence(trace).get("redacted_input"),
    ):
        method = _http_method_from_text(value)
        if method:
            return method
    return ""


def _normalize_http_method(value: Any) -> str:
    text = str(value or "").strip().upper()
    return re.sub(r"[^A-Z].*$", "", text)


def _http_method_from_text(value: Any) -> str:
    match = re.match(
        r"\s*(GET|HEAD|OPTIONS|POST|PUT|PATCH|DELETE)\b",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    return _normalize_http_method(match.group(1)) if match else ""


def _command_actions_from_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    tool = str(trace.get("tool") or "")
    if not tool or tool == "db_execute_query" or _is_http_trace(trace):
        return []
    command, operation = _trace_command_payload(trace)
    category = TOOL_CATEGORY.get(tool, "")
    if not command and not operation:
        return []
    if category in {"linux", "local"}:
        raw_actions = classify_linux_actions(command)
    elif category == "windows":
        raw_actions = classify_windows_actions(command)
    elif category == "network":
        raw_actions = classify_network_actions(command)
    elif tool == "redis_execute_command":
        raw_actions = classify_redis_actions(command)
    elif tool == "memcached_execute_command":
        raw_actions = classify_memcached_actions(command)
    elif tool == "mongodb_find":
        raw_actions = classify_mongodb_actions(command, operation=operation or "find")
    else:
        return []
    raw_actions = sorted(raw_actions, key=lambda action: ACTION_PRIORITY.get(action, 100))
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action_id in raw_actions:
        if action_id in seen:
            continue
        seen.add(action_id)
        detail = action_detail(action_id) or {
            "label": action_id,
            "description": "命中平台动作规则。",
            "severity": "medium",
        }
        actions.append({"id": action_id, **detail})
    return actions


def _trace_command_payload(trace: dict[str, Any]) -> tuple[str, str]:
    for payload in (
        _parsed_args_payload(trace),
        trace_result_meta(trace),
        _evidence_result_meta(trace),
        _parsed_result_payload(trace),
    ):
        command = payload.get("command") if isinstance(payload, dict) else None
        operation = payload.get("operation") if isinstance(payload, dict) else None
        if command or operation:
            return str(command or ""), str(operation or "")

    for value in (
        trace.get("args"),
        trace_evidence(trace).get("input_summary"),
        trace_evidence(trace).get("redacted_input"),
    ):
        text = str(value or "").strip()
        if text:
            return text, ""
    return "", ""


def _normalize_action(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    action_id = str(value.get("id") or "")
    label = str(value.get("label") or "")
    if not action_id or not label:
        return {}
    action = {
        "id": action_id,
        "label": label,
    }
    description = value.get("description")
    severity = value.get("severity")
    if isinstance(description, str):
        action["description"] = description
    if isinstance(severity, str):
        action["severity"] = severity
    return action


def _trace_statement_type(trace: dict[str, Any]) -> str:
    for payload in (
        trace_result_meta(trace),
        _evidence_result_meta(trace),
        _parsed_result_payload(trace),
    ):
        value = payload.get("statement_type") if isinstance(payload, dict) else None
        if value:
            return _normalize_statement_type(value)

    for value in (
        trace.get("args"),
        trace_evidence(trace).get("input_summary"),
        trace_evidence(trace).get("redacted_input"),
    ):
        statement_type = _statement_type_from_sql(value)
        if statement_type:
            return statement_type
    return ""


def _evidence_result_meta(trace: dict[str, Any]) -> dict[str, Any]:
    evidence_meta = trace_evidence(trace).get("result_meta")
    return evidence_meta if isinstance(evidence_meta, dict) else {}


def _parsed_args_payload(trace: dict[str, Any]) -> dict[str, Any]:
    raw = trace.get("args")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parsed_result_payload(trace: dict[str, Any]) -> dict[str, Any]:
    raw = trace.get("result")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_statement_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[^a-z_].*$", "", text)


def _statement_type_from_sql(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^(/\*.*?\*/|--[^\n]*(\n|$))", "", text, flags=re.DOTALL).strip()
    match = re.match(r"([a-zA-Z_]+)", text)
    return _normalize_statement_type(match.group(1)) if match else ""


def trace_runtime_summary(trace: dict[str, Any]) -> str:
    result_meta = trace_result_meta(trace)
    runtime = result_meta.get("runtime_execution") or result_meta.get("runtime_policy")
    if not isinstance(runtime, dict):
        evidence_meta = trace_evidence(trace).get("result_meta")
        if isinstance(evidence_meta, dict):
            runtime = evidence_meta.get("runtime_execution") or evidence_meta.get("runtime_policy")
    if not isinstance(runtime, dict):
        return ""
    parts: list[str] = []
    final_status = str(runtime.get("final_status") or "")
    error_type = str(runtime.get("error_type") or "")
    timeout_seconds = runtime.get("timeout_seconds")
    if final_status == "error":
        parts.append(
            f"timeout:{timeout_seconds}s"
            if error_type == "tool_timeout" and timeout_seconds
            else f"error:{error_type or 'tool_execution_failed'}"
        )
    if runtime.get("retried") is True:
        attempts = runtime.get("attempts")
        max_attempts = runtime.get("max_attempts")
        total = f"/{max_attempts}" if max_attempts else ""
        parts.append(f"retry:{attempts}{total}")
    return ",".join(parts)
