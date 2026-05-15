from __future__ import annotations

import json
from typing import Any

from core import dispatcher as dispatcher_module
from core.asset_protocols import (
    API_PROTOCOLS,
    CONTAINER_ASSET_TYPES,
    MIDDLEWARE_ASSET_TYPES,
    NETWORK_SSH_ASSET_TYPES,
    SQL_PROTOCOLS,
    STORAGE_ASSET_TYPES,
    resolve_asset_identity,
)
from core.tool_execution_policy import execute_with_runtime_policy, evaluate_tool_execution_gate
from core.tool_registry import tool_policy_metadata


HTTP_API_TOOL_PRIORITY = (
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "http_api_request",
)


class LegacyCommandServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def map_legacy_execute_tool_call(identity: dict[str, Any], command: str, tool_registry: Any) -> tuple[str, dict[str, Any]]:
    """Map legacy /execute command text to the protocol-native tool call."""
    protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    command = str(command or "").strip()

    if protocol == "ssh" and asset_type in NETWORK_SSH_ASSET_TYPES:
        return "network_cli_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in CONTAINER_ASSET_TYPES:
        return "container_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in MIDDLEWARE_ASSET_TYPES:
        return "middleware_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in STORAGE_ASSET_TYPES:
        return "storage_execute_command", {"command": command}
    if protocol == "ssh":
        return "linux_execute_command", {"command": command}
    if protocol == "winrm":
        return "winrm_execute_command", {"command": command}
    if protocol in SQL_PROTOCOLS:
        return "db_execute_query", {"sql": command}
    if protocol == "redis":
        return "redis_execute_command", {"command": command}
    if protocol == "mongodb":
        try:
            parsed = json.loads(command)
        except Exception:
            parsed = {"collection": command}
        if not isinstance(parsed, dict):
            parsed = {"collection": command}
        return "mongodb_find", {
            "database": parsed.get("database"),
            "collection": parsed.get("collection") or parsed.get("coll") or command,
            "filter": parsed.get("filter") or {},
            "projection": parsed.get("projection"),
            "limit": parsed.get("limit") or 100,
        }
    if protocol in API_PROTOCOLS:
        method = "GET"
        path = command or "/"
        parts = command.split(maxsplit=1)
        if parts and parts[0].upper() in {"GET", "HEAD", "POST"}:
            method = parts[0].upper()
            path = parts[1] if len(parts) > 1 else "/"
        active_tools = {
            tool.name
            for tool in tool_registry.available(
                {
                    "target_scope": "asset",
                    "asset_type": asset_type,
                    "protocol": protocol,
                    "extra_args": identity.get("extra_args") or {},
                }
            )
        }
        tool_name = next((candidate for candidate in HTTP_API_TOOL_PRIORITY if candidate in active_tools), "http_api_request")
        return tool_name, {"method": method, "path": path}
    if protocol == "snmp":
        return "snmp_get", {"oid": command}

    raise LegacyCommandServiceError(
        400,
        f"/execute 不支持 {asset_type}/{protocol}；请使用聊天会话原生工具或巡检接口。",
    )


async def execute_legacy_command_record(
    active_sessions: dict[str, Any],
    tool_registry: Any,
    *,
    session_id: str,
    command: str,
    dispatcher: Any | None = None,
) -> dict[str, Any]:
    if session_id not in active_sessions:
        raise LegacyCommandServiceError(404, "会话不存在或已断开")

    info = active_sessions[session_id]["info"]
    identity = resolve_asset_identity(
        info.get("asset_type"),
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    context = {
        **info,
        "session_id": session_id,
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "extra_args": identity["extra_args"],
    }
    tool_name, tool_args = map_legacy_execute_tool_call(identity, command, tool_registry)
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    needs_approval, approval_reason = resolved_dispatcher.check_approval_needed(tool_name, tool_args, context)
    runtime_tool_policy = tool_policy_metadata(tool_name)
    execution_gate_checker = getattr(resolved_dispatcher, "check_execution_gate", None)
    if callable(execution_gate_checker):
        execution_gate = execution_gate_checker(
            tool_name,
            tool_args,
            context,
            policy=runtime_tool_policy,
        )
    else:
        execution_gate = evaluate_tool_execution_gate(
            tool_name,
            safety_needs_approval=needs_approval,
            safety_reason=approval_reason,
            policy=runtime_tool_policy,
        )
    if execution_gate.approval_required:
        approval_sources = [
            source
            for source in ("runtime_policy", "safety_policy", "action_policy")
            if source in execution_gate.approval_sources
        ]
        raise LegacyCommandServiceError(
            409,
            _build_legacy_approval_error_payload(
                tool_name,
                execution_gate,
                runtime_tool_policy,
                approval_reason,
                approval_sources,
            )
        )

    runtime_execution: dict[str, Any] = {}
    result_str = await execute_with_runtime_policy(
        tool_name,
        lambda: resolved_dispatcher.route_and_execute(tool_name, tool_args, context),
        policy=runtime_tool_policy,
        runtime_stats=runtime_execution,
    )
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"success": False, "error": result_str}

    if not result.get("success"):
        message = result.get("error") or result.get("reason") or "执行失败"
        if result.get("runtime_policy"):
            raise LegacyCommandServiceError(
                400,
                {
                    "message": message,
                    "error": message,
                    "error_type": result.get("error_type"),
                    "runtime_policy": result.get("runtime_policy"),
                    "tool": result.get("tool") or tool_name,
                },
            )
        raise LegacyCommandServiceError(400, message)

    response = {
        "output": result.get("output") or result.get("data") or "",
        "has_error": result.get("has_error", False),
        "exit_status": result.get("exit_status", 0),
    }
    if runtime_execution:
        response["runtime_execution"] = runtime_execution
    return response


def _build_legacy_approval_error_payload(
    tool_name: str,
    execution_gate,
    runtime_tool_policy: dict[str, Any],
    approval_reason: str,
    approval_sources: list[str],
) -> dict[str, Any]:
    operation_mode = str(runtime_tool_policy.get("operation_mode") or "")
    approval_policy = str(runtime_tool_policy.get("approval_policy") or "")
    runtime_policy_required = "runtime_policy" in execution_gate.approval_sources
    return {
        "message": f"该操作需要后端审批：{execution_gate.reason}。请在聊天会话中执行，以便弹出审批确认。",
        "code": "approval_required",
        "tool": tool_name,
        "approval_sources": approval_sources,
        "safety_policy": {
            "required": "safety_policy" in execution_gate.approval_sources,
            "reason": approval_reason if "safety_policy" in execution_gate.approval_sources else "",
        },
        "runtime_policy": {
            "required": runtime_policy_required,
            "reason": execution_gate.reason if runtime_policy_required else "",
            "operation_mode": operation_mode,
            "approval_policy": approval_policy,
            "sources": list(execution_gate.approval_sources),
        },
        "policy": runtime_tool_policy,
    }
