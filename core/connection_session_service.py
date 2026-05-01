from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.asset_protocols import resolve_asset_identity
from core.connection_errors import classify_connection_error, connection_error_http_status
from core.connection_request_service import normalize_private_key_path


class ConnectionSessionServiceError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def _raise_connection_error(result: dict[str, Any], protocol: str = "") -> None:
    if result.get("error_code") and result.get("error_category"):
        error = {
            "code": result.get("error_code"),
            "category": result.get("error_category"),
            "message": result.get("message") or "连接失败",
            "raw_error": result.get("raw_error") or result.get("message") or "",
            "protocol": protocol,
        }
    else:
        error = classify_connection_error(result.get("message") or result.get("error"), protocol)
    raise ConnectionSessionServiceError(connection_error_http_status(error), error)


async def create_connection_session(
    req: Any,
    ssh_manager: Any,
    memory_db: Any,
    *,
    restored_password: str | None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    if req.target_scope == "global":
        result = await asyncio.to_thread(
            ssh_manager.connect_local,
            agent_profile=req.agent_profile,
            active_skills=req.active_skills,
            remark=req.remark or "全局总控",
            allow_modifications=req.allow_modifications,
            tags=req.tags or ["全局会话"],
            target_scope="global",
            scope_value=req.scope_value,
        )
        return {
            "status": "success",
            "message": "Global Session Established",
            "data": {"session_id": result["session_id"]},
        }

    identity = resolve_asset_identity(
        req.asset_type,
        req.protocol,
        req.extra_args,
        req.host,
        req.port,
        req.remark,
    )
    login_protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    extra_args = identity["extra_args"]

    if logger:
        logger.info(
            "API called: Connect to %s as %s/%s with profile %s, remark: %s",
            req.host,
            asset_type,
            login_protocol,
            req.agent_profile,
            req.remark,
        )

    result = await asyncio.to_thread(
        ssh_manager.connect,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        key_filename=normalize_private_key_path(req.private_key_path),
        allow_modifications=req.allow_modifications,
        active_skills=req.active_skills,
        agent_profile=req.agent_profile,
        remark=req.remark,
        asset_type=asset_type,
        protocol=login_protocol,
        extra_args=extra_args,
        tags=req.tags,
        target_scope=req.target_scope,
        scope_value=req.scope_value,
    )

    if result["success"]:
        memory_db.save_asset(
            remark=req.remark,
            host=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            asset_type=asset_type,
            protocol=login_protocol,
            agent_profile=req.agent_profile,
            extra_args=extra_args,
            skills=req.active_skills,
            tags=req.tags,
        )

    if not result["success"]:
        _raise_connection_error(result, login_protocol)

    return {
        "status": "success",
        "message": "Session Established",
        "data": {"session_id": result["session_id"]},
    }
