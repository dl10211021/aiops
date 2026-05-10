from __future__ import annotations

import re
from typing import Any


ASSET_TOOL_FAMILY_HINTS = {
    "db_execute_query": "database",
    "mongodb_find": "database",
    "redis_execute_command": "database",
    "memcached_execute_command": "database",
    "linux_execute_command": "os",
    "winrm_execute_command": "os",
    "container_execute_command": "container",
    "network_cli_execute_command": "network",
    "snmp_get": "network",
    "monitoring_api_query": "observability",
}


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", value.strip())
    return clean.strip("-")[:120] or "unknown"


def tool_family(tool_name: str) -> str:
    if tool_name in ASSET_TOOL_FAMILY_HINTS:
        return ASSET_TOOL_FAMILY_HINTS[tool_name]
    if tool_name.endswith("_api_request") or tool_name == "http_api_request":
        return "api"
    if tool_name.endswith("_execute_command"):
        return tool_name.rsplit("_execute_command", 1)[0] or "command"
    return "tool"


def asset_ref_from_context(context: dict[str, Any] | None) -> dict[str, Any]:
    context = context or {}
    return {
        "asset_id": context.get("asset_id"),
        "target_scope": context.get("target_scope") or "asset",
        "asset_type": context.get("asset_type"),
        "protocol": context.get("protocol"),
        "host": context.get("host"),
        "port": context.get("port"),
    }


def build_tool_evidence(
    *,
    tool_call_id: str,
    session_id: str,
    context: dict[str, Any] | None,
    tool_name: str,
    input_summary: str,
    output_preview: str,
    result_status: str,
    result_meta: dict[str, Any] | None = None,
    started_at: int | None = None,
    finished_at: int | None = None,
    approval_ref: str | None = None,
) -> dict[str, Any]:
    evidence_id = f"tev-{_slug(session_id)}-{_slug(tool_call_id or tool_name)}"
    evidence = {
        "evidence_id": evidence_id,
        "session_id": session_id,
        "asset_ref": asset_ref_from_context(context),
        "tool_name": tool_name,
        "tool_family": tool_family(tool_name),
        "input_summary": input_summary,
        "redacted_input": input_summary,
        "output_preview": output_preview,
        "result_status": result_status if result_status in {"done", "error"} else "done",
        "result_meta": result_meta or {},
        "approval_ref": approval_ref,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    return {key: value for key, value in evidence.items() if value is not None}
