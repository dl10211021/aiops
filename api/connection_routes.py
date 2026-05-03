import asyncio
import logging

from fastapi import APIRouter, HTTPException

from api.errors import raise_http_error
from api.response_mappers.connections import (
    legacy_command_response_kwargs,
    session_closed_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.connections import (
    CommandRequest,
    ConnectionInspectionRequest,
    ConnectionRequest,
)
from connections.ssh_manager import ssh_manager
from core.connection_inspection_service import inspect_connection_request
from core.connection_request_service import (
    asset_matches_connection_request,
    get_login_protocol_from_request,
    restore_connection_request_secrets,
)
from core.connection_session_service import (
    ConnectionSessionServiceError,
    create_connection_session,
)
from core.connection_test_service import run_connection_test
from core.legacy_command_service import (
    LegacyCommandServiceError,
    execute_legacy_command_record,
)
from core.tool_registry import tool_registry


logger = logging.getLogger(__name__)
router = APIRouter()


def get_login_protocol(req: ConnectionRequest) -> str:
    return get_login_protocol_from_request(req)


def asset_matches_request(asset: dict, req: ConnectionRequest) -> bool:
    return asset_matches_connection_request(asset, req)


def get_restored_connection_request(
    req: ConnectionRequest,
) -> tuple[ConnectionRequest, str | None]:
    """Restore masked asset secrets from persisted records before connection flows."""
    return restore_connection_request_secrets(req)


@router.post("/connect/test", response_model=ResponseModel)
async def test_connection(req: ConnectionRequest):
    req, restored_password = get_restored_connection_request(req)
    result = await run_connection_test(req, restored_password)
    return ResponseModel(**result)


@router.post("/connect/inspect", response_model=ResponseModel)
async def inspect_connection(req: ConnectionInspectionRequest):
    """临时建立会话并执行只读巡检，默认巡检后自动断开。"""
    req, restored_password = get_restored_connection_request(req)
    result = await inspect_connection_request(
        req,
        restored_password=restored_password,
    )
    return ResponseModel(**result)


@router.post("/connect", response_model=ResponseModel)
async def create_ssh_connection(req: ConnectionRequest):
    """建立与远程系统的会话 (支持 SSH长连接 或 虚拟凭据会话)"""
    req, restored_password = get_restored_connection_request(req)

    try:
        result = await create_connection_session(
            req,
            ssh_manager,
            restored_password=restored_password,
            logger=logger,
        )
    except ConnectionSessionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**result)


@router.post("/execute", response_model=ResponseModel)
async def execute_remote_command(req: CommandRequest):
    """
    大模型使用的底层“Skill”核心：
    在已建立的 Session 中下发指令（如 uptime, ps aux）。
    """
    logger.info(f"API called: Executing legacy command on session {req.session_id}")

    try:
        data = await execute_legacy_command_record(
            ssh_manager.active_sessions,
            tool_registry,
            session_id=req.session_id,
            command=req.command,
        )
    except LegacyCommandServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(**legacy_command_response_kwargs(data))


@router.delete("/disconnect/{session_id}", response_model=ResponseModel)
async def close_ssh_connection(session_id: str):
    """大模型或者前端关闭会话释放资源"""
    success = await asyncio.to_thread(ssh_manager.disconnect, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return ResponseModel(**session_closed_response_kwargs())
