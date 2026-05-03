from __future__ import annotations

from collections.abc import MutableMapping

from core.session_groups import (
    DEFAULT_SESSION_GROUP,
    apply_primary_session_group,
    normalize_session_group_name,
)


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


def set_session_group(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    group_name: str,
) -> tuple[MutableMapping, str]:
    info = require_session_info(active_sessions, session_id)
    normalized_group = normalize_session_group_name(group_name)
    if not normalized_group:
        raise SessionRuntimeError(422, "会话组名称不能为空")
    try:
        info["tags"] = apply_primary_session_group(
            info.get("tags") or [],
            normalized_group,
        )
    except ValueError as exc:
        raise SessionRuntimeError(422, str(exc)) from exc
    return info, normalized_group


def _normalized_secondary_tags(
    tags: list[str] | None,
    *,
    current_group: str,
    next_group: str,
) -> list[str]:
    secondary_tags: list[str] = []
    blocked_primary_tags = {current_group, next_group}
    for item in tags or []:
        tag = normalize_session_group_name(item)
        if not tag or tag in blocked_primary_tags or tag in secondary_tags:
            continue
        secondary_tags.append(tag)
    return secondary_tags


def set_session_metadata(
    active_sessions: MutableMapping[str, dict],
    session_id: str,
    *,
    remark: str | None = None,
    group_name: str | None = None,
    tags: list[str] | None = None,
) -> tuple[MutableMapping, str]:
    info = require_session_info(active_sessions, session_id)
    current_tags = info.get("tags") or []
    current_group = (
        normalize_session_group_name(current_tags[0] if current_tags else None)
        or DEFAULT_SESSION_GROUP
    )
    normalized_group = (
        normalize_session_group_name(group_name)
        if group_name is not None
        else current_group
    )
    if not normalized_group:
        raise SessionRuntimeError(422, "会话组名称不能为空")

    if remark is not None:
        info["remark"] = str(remark).strip()[:200]

    if tags is None:
        try:
            info["tags"] = apply_primary_session_group(current_tags, normalized_group)
        except ValueError as exc:
            raise SessionRuntimeError(422, str(exc)) from exc
    else:
        secondary_tags = _normalized_secondary_tags(
            tags,
            current_group=current_group,
            next_group=normalized_group,
        )
        info["tags"] = [normalized_group, *secondary_tags]

    return info, normalized_group
