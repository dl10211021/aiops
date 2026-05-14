from __future__ import annotations

from typing import Any

from core.asset_protocols import resolve_asset_identity
from core.tool_registry import tool_public_dict


class SessionToolContextError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def build_session_info_for_tools(active_sessions: dict[str, dict], session_id: str) -> dict[str, Any]:
    if session_id not in active_sessions:
        raise SessionToolContextError(404, "会话不存在或已断开")
    info = dict(active_sessions[session_id]["info"])
    info["session_id"] = session_id
    return info


def build_session_tool_context(info: dict[str, Any]) -> dict[str, Any]:
    identity = resolve_asset_identity(
        info.get("asset_type"),
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    return {
        "session_id": info.get("session_id"),
        "target_scope": info.get("target_scope", "asset"),
        "scope_value": info.get("scope_value"),
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "host": info.get("host"),
        "port": info.get("port"),
        "remark": info.get("remark"),
        "extra_args": identity["extra_args"],
    }


def build_session_tools_response(tool_registry, info: dict[str, Any]) -> dict[str, Any]:
    context = build_session_tool_context(info)
    catalog = tool_registry.catalog(context)
    active_tools = [
        tool["name"]
        for toolset in catalog["toolsets"]
        for tool in toolset["tools"]
        if tool.get("enabled")
    ]
    active_tool_details = [tool_public_dict(tool_name) for tool_name in active_tools]
    return {
        **catalog,
        "active_tools": active_tools,
        "active_tool_details": active_tool_details,
        "context": {
            "target_scope": context["target_scope"],
            "asset_type": context["asset_type"],
            "protocol": context["protocol"],
            "host": context["host"],
            "port": context["port"],
        },
    }


def build_session_tools_payload_for_session(
    active_sessions: dict[str, dict],
    tool_registry,
    session_id: str,
) -> dict[str, Any]:
    return build_session_tools_response(
        tool_registry,
        build_session_info_for_tools(active_sessions, session_id),
    )
