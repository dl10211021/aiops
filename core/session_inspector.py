"""Read-only session inspection routines."""

from __future__ import annotations

from typing import Any

from connections.ssh_manager import ssh_manager
from core.asset_protocols import (
    API_PROTOCOLS,
    SERVICE_ASSET_TYPES,
    SERVICE_PROBE_PROTOCOLS,
    SQL_PROTOCOLS,
    SNMP_PROTOCOLS,
    get_asset_definition,
    normalize_protocol,
)
from core.session_inspection_profiles import (
    http_probe_url as _http_probe_url,
    inspect_http_api as _inspect_http_api,
    inspect_linux_ssh,
    inspect_memcached,
    inspect_mongodb as _inspect_mongodb,
    inspect_network_cli,
    inspect_redis as _inspect_redis,
    inspect_service_probe,
    inspect_snmp as _inspect_snmp,
    inspect_sql as _inspect_sql,
    inspect_winrm as _inspect_winrm,
)
from core.session_inspection_template_runner import run_inspection_template


def _profile_for(asset_type: str, protocol: str) -> str | None:
    definition = get_asset_definition(asset_type)
    if definition:
        return definition.get("inspection_profile")
    if protocol == "ssh" and asset_type in {"ssh", "linux", "kvm"}:
        return "linux"
    if protocol == "winrm":
        return "winrm"
    return None


async def _inspect_with_template(
    session_id: str,
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    return await run_inspection_template(session_id, info, asset_type, protocol, template, ssh_manager)


async def inspect_session(session_id: str) -> dict[str, Any]:
    session = ssh_manager.active_sessions.get(session_id)
    if not session:
        return {
            "status": "error",
            "supported": False,
            "message": "会话不存在或已断开",
            "checks": [],
        }

    info = session.get("info", {})
    asset_type = str(info.get("asset_type") or "").lower()
    protocol = normalize_protocol(
        asset_type,
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    profile = _profile_for(asset_type, protocol)

    try:
        from core.inspection_templates import find_matching_template

        template = find_matching_template(asset_type, protocol)
    except Exception:
        template = None
    if template:
        return await _inspect_with_template(session_id, info, asset_type, protocol, template)

    if protocol == "ssh" and profile == "linux":
        return await inspect_linux_ssh(session_id, asset_type, protocol, ssh_manager)

    if protocol == "ssh" and profile == "network_cli":
        return await inspect_network_cli(session_id, asset_type, protocol, ssh_manager)

    if protocol == "winrm":
        return await _inspect_winrm(info, asset_type, protocol)

    if protocol in SQL_PROTOCOLS:
        return await _inspect_sql(info, asset_type, protocol)

    if protocol == "redis":
        return await _inspect_redis(info, asset_type, protocol)

    if protocol == "memcached":
        return await inspect_memcached(info, asset_type, protocol)

    if protocol == "mongodb":
        return await _inspect_mongodb(info, asset_type, protocol)

    if protocol in SERVICE_PROBE_PROTOCOLS or asset_type in SERVICE_ASSET_TYPES:
        return await inspect_service_probe(info, asset_type, protocol)

    if protocol in API_PROTOCOLS:
        return await _inspect_http_api(info, asset_type, protocol)

    if protocol in SNMP_PROTOCOLS:
        return await _inspect_snmp(info, asset_type, protocol)

    return {
        "status": "unsupported",
        "supported": False,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": profile,
        "message": f"{asset_type or 'unknown'}/{protocol} 暂未接入深度巡检；当前已支持 Linux/KVM SSH、存储节点 SSH、网络设备 SSH CLI、Windows WinRM、SQL、Redis、MongoDB、SNMP 与 HTTP/API 只读巡检。",
        "checks": [],
    }
