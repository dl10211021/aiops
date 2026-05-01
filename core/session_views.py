"""Public session view builders used by API routes."""

from __future__ import annotations

from typing import Any

from core.asset_protocols import resolve_asset_identity
from core.session_groups import DEFAULT_SESSION_GROUP, normalize_session_group_name


def mask_sensitive_extra_args(
    extra_args: dict[str, Any],
    sensitive_keys: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    masked = dict(extra_args or {})
    for key in sensitive_keys:
        if key in masked and masked[key]:
            masked[key] = "********"
    return masked


def build_active_session_view(
    session_id: str,
    info: dict[str, Any],
    *,
    is_streaming: bool,
    sensitive_keys: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    identity = resolve_asset_identity(
        info.get("asset_type"),
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    tags = info.get("tags") or [DEFAULT_SESSION_GROUP]
    group_name = normalize_session_group_name(tags[0] if tags else DEFAULT_SESSION_GROUP) or DEFAULT_SESSION_GROUP
    return {
        "id": session_id,
        "host": info.get("host"),
        "remark": info.get("remark"),
        "isReadWriteMode": info.get("allow_modifications"),
        "skills": info.get("active_skills", []),
        "agentProfile": info.get("agent_profile"),
        "user": info.get("username"),
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "extra_args": mask_sensitive_extra_args(identity["extra_args"], sensitive_keys),
        "heartbeatEnabled": info.get("heartbeat_enabled", False),
        "tags": tags,
        "group_name": group_name,
        "target_scope": info.get("target_scope", "asset"),
        "scope_value": info.get("scope_value"),
        "isStreaming": is_streaming,
    }
