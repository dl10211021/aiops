from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from core.asset_protocols import resolve_asset_identity
from core.connection_request_service import normalize_private_key_path
from core.connection_test_service import connection_error_result
from core.session_inspection_service import inspect_active_session_record
from connections.ssh_manager import ssh_manager as default_ssh_manager


InspectSessionCallable = Callable[[str], Awaitable[dict[str, Any]]]


def global_inspection_result() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "全局总控会话检查完成。",
        "data": {
            "session_id": None,
            "kept_session": False,
            "inspection": {
                "status": "success",
                "supported": True,
                "asset_type": "virtual",
                "protocol": "virtual",
                "profile": "global",
                "summary": "全局总控会话无需单资产连通性巡检；创建后可使用 list_active_sessions、dispatch_sub_agents、search_assets_by_tag 等编排工具。",
                "checks": [],
            },
        },
    }


async def inspect_connection_session(
    req: Any,
    ssh_manager: Any,
    inspect_session: InspectSessionCallable,
    *,
    restored_password: str | None,
) -> dict[str, Any]:
    if req.target_scope == "global":
        return global_inspection_result()

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

    result = await asyncio.to_thread(
        ssh_manager.connect,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        key_filename=normalize_private_key_path(req.private_key_path),
        allow_modifications=False,
        active_skills=req.active_skills,
        agent_profile=req.agent_profile,
        remark=req.remark or "巡检测试会话",
        asset_type=asset_type,
        protocol=login_protocol,
        extra_args=extra_args,
        tags=req.tags,
        target_scope=req.target_scope,
        scope_value=req.scope_value,
    )

    if not result.get("success"):
        if result.get("error_code") and result.get("error_category"):
            error = {
                "code": result.get("error_code"),
                "category": result.get("error_category"),
                "message": result.get("message", "连接失败"),
                "raw_error": result.get("raw_error") or result.get("message", ""),
                "protocol": login_protocol,
            }
            return {"status": "error", "message": error["message"], "data": {"error": error}}
        return connection_error_result(result.get("message", "连接失败"), login_protocol)

    session_id = result["session_id"]
    try:
        report = await inspect_session(session_id)
    finally:
        if not req.keep_session:
            await asyncio.to_thread(ssh_manager.disconnect, session_id)

    return {
        "status": "success" if report.get("status") in {"success", "warning"} else report.get("status", "error"),
        "message": report.get("summary") or report.get("message", ""),
        "data": {
            "session_id": session_id if req.keep_session else None,
            "kept_session": req.keep_session,
            "inspection": report,
        },
    }


async def inspect_connection_request(
    req: Any,
    *,
    restored_password: str | None,
    ssh_manager: Any = default_ssh_manager,
    inspector: InspectSessionCallable = inspect_active_session_record,
) -> dict[str, Any]:
    return await inspect_connection_session(
        req,
        ssh_manager,
        inspector,
        restored_password=restored_password,
    )
