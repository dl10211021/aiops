import logging

from fastapi import APIRouter

from api.errors import raise_http_error
from api.mappers import (
    active_sessions_response_kwargs,
    all_sessions_poll_response_kwargs,
    chat_stop_response_kwargs,
    session_commands_response_kwargs,
    session_group_response_kwargs,
    session_group_update_kwargs,
    session_heartbeat_update_kwargs,
    session_heartbeat_updated_response_kwargs,
    session_poll_response_kwargs,
    session_permission_update_kwargs,
    session_permission_updated_response_kwargs,
    session_skills_updated_response_kwargs,
    tool_catalog_response_kwargs,
)
from api.schemas import (
    HeartbeatUpdateRequest,
    PermissionUpdateRequest,
    ResponseModel,
    SessionGroupUpdateRequest,
    SkillsUpdateRequest,
)
from connections.ssh_manager import ssh_manager
from core.active_sessions_service import build_active_sessions_payload
from core.chat_session_service import request_session_stop
from core.session_commands import build_session_commands_payload_for_session
from core.session_runtime import (
    SessionRuntimeError,
    drain_all_pending_messages,
    drain_session_pending_messages,
    set_session_group,
    set_session_heartbeat,
    set_session_permission,
    set_session_skills,
)
from core.session_tool_context import (
    SessionToolContextError,
    build_session_tools_payload_for_session,
)
from core.tool_registry import tool_registry


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/session/{session_id}/stop", response_model=ResponseModel)
async def stop_chat_session(session_id: str):
    """【新功能】终止当前会话中正在生成的长流响应/执行任务"""
    request_session_stop(session_id)
    return ResponseModel(**chat_stop_response_kwargs())


@router.put("/session/{session_id}/permission", response_model=ResponseModel)
async def update_session_permission(session_id: str, req: PermissionUpdateRequest):
    """【新功能】动态提权/降权：在不中断 SSH 的情况下，修改当前会话的 AI 修改权限"""
    update = session_permission_update_kwargs(req)
    try:
        set_session_permission(
            ssh_manager.active_sessions,
            session_id,
            **update,
        )
    except SessionRuntimeError as exc:
        raise_http_error(exc)
    logger.info(
        f"Session {session_id} permissions changed to: {update['allow_modifications']}"
    )

    return ResponseModel(**session_permission_updated_response_kwargs())


@router.put("/session/{session_id}/heartbeat", response_model=ResponseModel)
async def update_session_heartbeat(session_id: str, req: HeartbeatUpdateRequest):
    """【新功能】动态开启或关闭心跳巡检"""
    update = session_heartbeat_update_kwargs(req)
    try:
        set_session_heartbeat(
            ssh_manager.active_sessions,
            session_id,
            **update,
        )
    except SessionRuntimeError as exc:
        raise_http_error(exc)

    if update["master_interval"] is not None:
        logger.info(
            f"Session {session_id} master_interval updated to: {update['master_interval']}s"
        )

    logger.info(f"Session {session_id} heartbeat changed to: {update['heartbeat_enabled']}")

    return ResponseModel(**session_heartbeat_updated_response_kwargs())


@router.get("/sessions/poll_all", response_model=ResponseModel)
async def poll_all_sessions_messages():
    """【新功能】全局长轮询获取所有后台会话的待推送消息，极大地降低大规模纳管时的请求数量"""
    with ssh_manager._sessions_lock:
        updates = drain_all_pending_messages(ssh_manager.active_sessions)

    return ResponseModel(**all_sessions_poll_response_kwargs(updates))


@router.get("/session/{session_id}/poll", response_model=ResponseModel)
async def poll_session_messages(session_id: str):
    """【新功能】前端长轮询获取后台心跳主动推送的消息"""
    try:
        with ssh_manager._sessions_lock:
            pending = drain_session_pending_messages(
                ssh_manager.active_sessions,
                session_id,
                missing_detail="Session disconnected",
            )
    except SessionRuntimeError as exc:
        raise_http_error(exc)

    return ResponseModel(**session_poll_response_kwargs(pending))


@router.put("/session/{session_id}/skills", response_model=ResponseModel)
async def update_session_skills(session_id: str, req: SkillsUpdateRequest):
    """【新功能】动态修改挂载技能包：在不中断会话的情况下，挂载或卸载 AI 技能"""
    try:
        set_session_skills(ssh_manager.active_sessions, session_id, req.active_skills)
    except SessionRuntimeError as exc:
        raise_http_error(exc)
    logger.info(f"Session {session_id} active skills changed to: {req.active_skills}")

    return ResponseModel(**session_skills_updated_response_kwargs())


@router.put("/session/{session_id}/group", response_model=ResponseModel)
async def update_session_group(session_id: str, req: SessionGroupUpdateRequest):
    """更新活跃会话的主分组；底层复用现有 tags[0]，保持旧会话结构兼容。"""
    update = session_group_update_kwargs(req)
    try:
        info, group_name = set_session_group(
            ssh_manager.active_sessions,
            session_id,
            **update,
        )
    except SessionRuntimeError as exc:
        raise_http_error(exc)
    logger.info("Session %s group changed to: %s", session_id, group_name)

    return ResponseModel(**session_group_response_kwargs(session_id, info, group_name))


@router.get("/sessions/active", response_model=ResponseModel)
async def get_active_sessions():
    """【新功能】前端刷新页面时同步当前后端的活跃会话"""
    sessions_data = build_active_sessions_payload(ssh_manager.active_sessions)
    return ResponseModel(**active_sessions_response_kwargs(sessions_data))


@router.get("/tools/catalog", response_model=ResponseModel)
async def get_tool_catalog():
    """返回平台内置工具目录。仅包含工具元数据，不包含任何资产凭据。"""
    return ResponseModel(**tool_catalog_response_kwargs(tool_registry.catalog()))


@router.get("/session/{session_id}/tools", response_model=ResponseModel)
async def get_session_tools(session_id: str):
    """返回指定会话当前会暴露给模型的工具集。"""
    try:
        payload = build_session_tools_payload_for_session(
            ssh_manager.active_sessions,
            tool_registry,
            session_id,
        )
    except SessionToolContextError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_commands_response_kwargs(payload))


@router.get("/session/{session_id}/commands", response_model=ResponseModel)
async def get_session_commands(session_id: str):
    """返回当前会话可用 Slash Commands；由后端根据资产协议生成 prompt。"""
    try:
        payload = await build_session_commands_payload_for_session(
            ssh_manager.active_sessions,
            tool_registry,
            session_id,
        )
    except SessionToolContextError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_commands_response_kwargs(payload))
