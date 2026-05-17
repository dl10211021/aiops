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


def _session_group(info: MutableMapping) -> str:
    tags = info.get("tags") or []
    return (
        normalize_session_group_name(tags[0] if tags else None)
        or DEFAULT_SESSION_GROUP
    )


def sync_multi_agent_session_permissions(
    active_sessions: MutableMapping[str, dict],
    *,
    scope: str,
    allow_modifications: bool,
    group_name: str | None = None,
    target_session_ids: list[str] | None = None,
) -> dict:
    normalized_scope = str(scope or "").strip().lower()
    if normalized_scope not in {"global", "group"}:
        raise SessionRuntimeError(422, "调度范围必须是 global 或 group")

    normalized_group = normalize_session_group_name(group_name)
    if normalized_scope == "group" and not normalized_group:
        raise SessionRuntimeError(422, "分组模式必须指定会话组")

    requested_ids: list[str] = []
    seen_requested_ids: set[str] = set()
    for item in target_session_ids or []:
        session_id = str(item or "").strip()
        if not session_id or session_id in seen_requested_ids:
            continue
        requested_ids.append(session_id)
        seen_requested_ids.add(session_id)
    selected_ids = requested_ids or list(active_sessions.keys())
    changed_sessions: list[dict] = []
    skipped_sessions: list[dict] = []

    for session_id in selected_ids:
        session_data = active_sessions.get(session_id)
        if not session_data:
            skipped_sessions.append({"session_id": session_id, "reason": "missing_session"})
            continue
        info = session_data.get("info") or {}
        current_group = _session_group(info)
        if normalized_scope == "group" and current_group != normalized_group:
            skipped_sessions.append(
                {
                    "session_id": session_id,
                    "reason": "group_mismatch",
                    "group_name": current_group,
                }
            )
            continue
        previous = bool(info.get("allow_modifications", False))
        info["allow_modifications"] = bool(allow_modifications)
        changed_sessions.append(
            {
                "session_id": session_id,
                "group_name": current_group,
                "previous_allow_modifications": previous,
                "allow_modifications": bool(allow_modifications),
            }
        )

    return {
        "scope": normalized_scope,
        "group_name": normalized_group if normalized_scope == "group" else "",
        "permission_mode": "readwrite" if allow_modifications else "readonly",
        "allow_modifications": bool(allow_modifications),
        "requested_session_ids": requested_ids,
        "changed_sessions": changed_sessions,
        "skipped_sessions": skipped_sessions,
        "target_count": len(changed_sessions),
        "skipped_count": len(skipped_sessions),
    }


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
