from __future__ import annotations

from collections.abc import MutableMapping


class SessionRuntimeError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def require_session_info(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
) -> MutableMapping:
    if session_id not in active_sessions:
        raise SessionRuntimeError(404, "会话不存在或已断开")
    return active_sessions[session_id]["info"]


def set_session_permission(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    allow_modifications: bool,
) -> MutableMapping:
    info = require_session_info(active_sessions, session_id)
    info["allow_modifications"] = allow_modifications
    return info


def set_session_heartbeat(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    heartbeat_enabled: bool,
    master_interval: int | None = None,
) -> MutableMapping:
    info = require_session_info(active_sessions, session_id)
    info["heartbeat_enabled"] = heartbeat_enabled
    if heartbeat_enabled:
        info["last_active"] = 0

    if master_interval is not None:
        if "extra_args" not in info:
            info["extra_args"] = {}
        info["extra_args"]["master_interval"] = master_interval
    return info


def set_session_skills(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    active_skills: list[str],
) -> MutableMapping:
    info = require_session_info(active_sessions, session_id)
    info["active_skills"] = active_skills
    return info


def drain_session_pending_messages(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    missing_detail: str = "会话不存在或已断开",
) -> list:
    if session_id not in active_sessions:
        raise SessionRuntimeError(404, missing_detail)
    info = active_sessions[session_id]["info"]
    pending = info.get("pending_messages", [])
    if pending:
        info["pending_messages"] = []
    return pending


def drain_all_pending_messages(active_sessions: MutableMapping[str, dict]) -> dict:
    updates = {}
    for session_id, session_data in active_sessions.items():
        pending = session_data["info"].get("pending_messages", [])
        if pending:
            updates[session_id] = pending.copy()
            session_data["info"]["pending_messages"] = []
    return updates
