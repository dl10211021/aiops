from __future__ import annotations

from typing import Any

from core.asset_protocols import resolve_asset_identity


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
    return {
        **catalog,
        "active_tools": active_tools,
        "context": {
            "target_scope": context["target_scope"],
            "asset_type": context["asset_type"],
            "protocol": context["protocol"],
            "host": context["host"],
            "port": context["port"],
        },
    }
