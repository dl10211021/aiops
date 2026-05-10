from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


TARGET_PATTERN = re.compile(
    r"(?:^|[^\w:/.-])"
    r"(?P<asset>[A-Za-z][A-Za-z0-9_-]{1,40})/"
    r"(?P<protocol>[A-Za-z][A-Za-z0-9_-]{1,40})"
    r"\s+"
    r"(?P<host>(?:\d{1,3}\.){3}\d{1,3}|[A-Za-z0-9_.:-]{3,255})"
)

TOKEN_ALIASES = {
    "postgres": "postgresql",
    "pg": "postgresql",
    "sqlserver": "mssql",
    "sql_server": "mssql",
    "dm": "dameng",
}


@dataclass(frozen=True)
class SessionTargetMismatch:
    requested_asset_type: str
    requested_protocol: str
    requested_host: str
    current_asset_type: str
    current_protocol: str
    current_host: str


def _field(context: Any, name: str) -> str:
    if isinstance(context, dict):
        return str(context.get(name) or "")
    return str(getattr(context, name, "") or "")


def _normalize_token(value: str) -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    return TOKEN_ALIASES.get(token, token)


def _normalize_host(value: str) -> str:
    return str(value or "").strip().lower().strip("`'\"，。；;、")


def find_session_target_mismatch(
    text: str,
    session_context: Any,
) -> SessionTargetMismatch | None:
    """Detect explicit asset targets that do not belong to the active session."""
    current_asset = _normalize_token(_field(session_context, "asset_type"))
    current_protocol = _normalize_token(_field(session_context, "protocol"))
    current_host = _normalize_host(_field(session_context, "host"))
    if not current_asset and not current_protocol and not current_host:
        return None

    for match in TARGET_PATTERN.finditer(str(text or "")):
        requested_asset = _normalize_token(match.group("asset"))
        requested_protocol = _normalize_token(match.group("protocol"))
        requested_host = _normalize_host(match.group("host"))
        asset_mismatch = bool(current_asset and requested_asset != current_asset)
        protocol_mismatch = bool(current_protocol and requested_protocol != current_protocol)
        host_mismatch = bool(current_host and requested_host != current_host)
        if asset_mismatch or protocol_mismatch or host_mismatch:
            return SessionTargetMismatch(
                requested_asset_type=requested_asset,
                requested_protocol=requested_protocol,
                requested_host=requested_host,
                current_asset_type=current_asset,
                current_protocol=current_protocol,
                current_host=current_host,
            )
    return None


def target_mismatch_message(mismatch: SessionTargetMismatch) -> str:
    requested = (
        f"{mismatch.requested_asset_type}/{mismatch.requested_protocol} "
        f"{mismatch.requested_host}"
    )
    current = (
        f"{mismatch.current_asset_type}/{mismatch.current_protocol} "
        f"{mismatch.current_host}"
    )
    return (
        f"已拦截本次请求：你指定的目标是 `{requested}`，但当前会话绑定的是 `{current}`。\n\n"
        "为避免把 Linux/Windows/网络设备命令写进 Oracle 会话，OpsCore 不会在当前会话执行这个请求。"
        "请切换到目标资产会话后重新发送，或把请求改成当前会话目标。"
    )
