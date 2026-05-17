import asyncio
import contextlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from api.errors import raise_http_error
from api.response_mappers.session import (
    active_sessions_response_kwargs,
    all_sessions_poll_response_kwargs,
    multi_agent_permission_sync_kwargs,
    multi_agent_permission_synced_response_kwargs,
    session_commands_response_kwargs,
    session_group_response_kwargs,
    session_group_update_kwargs,
    session_heartbeat_update_kwargs,
    session_heartbeat_updated_response_kwargs,
    session_metadata_response_kwargs,
    session_metadata_update_kwargs,
    session_poll_response_kwargs,
    session_permission_update_kwargs,
    session_permission_updated_response_kwargs,
    session_status_response_kwargs,
    session_skills_updated_response_kwargs,
    tool_catalog_response_kwargs,
)
from api.response_mappers.chat import chat_stop_response_kwargs
from api.schema_models.common import ResponseModel
from api.schema_models.sessions import (
    HeartbeatUpdateRequest,
    MultiAgentPermissionSyncRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionMetadataUpdateRequest,
    SkillsUpdateRequest,
)
from connections.ssh_manager import ssh_manager
from core import chat_runs as chat_runs_module
from core.active_sessions_service import build_active_sessions_payload
from core.chat_session_service import request_session_stop
from core.memory import memory_db
from core.session_commands import build_session_commands_payload_for_session
from core.session_runtime import (
    SessionRuntimeError,
    drain_all_pending_messages,
    drain_session_pending_messages,
    require_session_info,
    set_session_group,
    set_session_heartbeat,
    set_session_metadata,
    set_session_permission,
    set_session_skills,
    sync_multi_agent_session_permissions,
)
from core.session_tool_context import (
    SessionToolContextError,
    build_session_tools_payload_for_session,
)
from core.security import is_authorized_request
from core.tool_center_service import build_tool_center_catalog
from core.tool_registry import tool_registry


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/session/{session_id}/stop", response_model=ResponseModel)
async def stop_chat_session(session_id: str):
    """【新功能】终止当前会话中正在生成的长流响应/执行任务"""
    with ssh_manager._sessions_lock:
        request_session_stop(
            session_id,
            active_sessions=ssh_manager.active_sessions,
            memory_db=memory_db,
        )
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


@router.put("/sessions/multi-agent/permissions", response_model=ResponseModel)
async def sync_multi_agent_permissions(req: MultiAgentPermissionSyncRequest):
    """按全局或分组范围批量同步多 Agent 目标会话权限。"""
    update = multi_agent_permission_sync_kwargs(req)
    try:
        with ssh_manager._sessions_lock:
            result = sync_multi_agent_session_permissions(
                ssh_manager.active_sessions,
                **update,
            )
    except SessionRuntimeError as exc:
        raise_http_error(exc)
    logger.info(
        "Multi-agent permission sync: scope=%s group=%s mode=%s changed=%s skipped=%s",
        result["scope"],
        result["group_name"],
        result["permission_mode"],
        result["target_count"],
        result["skipped_count"],
    )

    return ResponseModel(**multi_agent_permission_synced_response_kwargs(result))


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


@router.put("/session/{session_id}/metadata", response_model=ResponseModel)
async def update_session_metadata(session_id: str, req: SessionMetadataUpdateRequest):
    """更新活跃会话的显示名称、主分组和二级标签，不改变连接目标或执行上下文。"""
    update = session_metadata_update_kwargs(req)
    try:
        info, group_name = set_session_metadata(
            ssh_manager.active_sessions,
            session_id,
            **update,
        )
    except SessionRuntimeError as exc:
        raise_http_error(exc)
    logger.info("Session %s metadata changed; group=%s", session_id, group_name)

    return ResponseModel(**session_metadata_response_kwargs(session_id, info, group_name))


@router.get("/sessions/active", response_model=ResponseModel)
async def get_active_sessions():
    """【新功能】前端刷新页面时同步当前后端的活跃会话"""
    sessions_data = build_active_sessions_payload(ssh_manager.active_sessions)
    return ResponseModel(**active_sessions_response_kwargs(sessions_data))


@router.get("/session/{session_id}/status", response_model=ResponseModel)
async def get_session_status(session_id: str):
    """返回单个会话的轻量运行状态，避免前端恢复流时拉取完整会话清单。"""
    try:
        with ssh_manager._sessions_lock:
            require_session_info(ssh_manager.active_sessions, session_id)
            is_streaming = chat_runs_module.is_chat_running(session_id)
    except SessionRuntimeError as exc:
        raise_http_error(exc)

    return ResponseModel(**session_status_response_kwargs(session_id, is_streaming))


@router.get("/tools/catalog", response_model=ResponseModel)
async def get_tool_catalog():
    """返回平台内置工具目录。仅包含工具元数据，不包含任何资产凭据。"""
    return ResponseModel(**tool_catalog_response_kwargs(tool_registry.catalog()))


@router.get("/tools/center", response_model=ResponseModel)
async def get_tool_center():
    """返回工具中心只读目录，包含当前模型工具和受控未开放工具。"""
    return ResponseModel(**tool_catalog_response_kwargs(build_tool_center_catalog(tool_registry)))


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


@router.websocket("/session/{session_id}/terminal/ws")
async def terminal_websocket(session_id: str, websocket: WebSocket):
    """Interactive SSH PTY stream for browser terminals."""
    if not _websocket_authorized(websocket):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing or invalid OpsCore API token",
        )
        return

    await websocket.accept()
    channel = None
    reader_task: asyncio.Task | None = None
    try:
        cols = _int_query(websocket, "cols", 140)
        rows = _int_query(websocket, "rows", 42)
        channel = await asyncio.to_thread(
            ssh_manager.open_terminal_channel,
            session_id,
            width=cols,
            height=rows,
        )
        reader_task = asyncio.create_task(_terminal_reader_loop(websocket, channel))
        await _terminal_writer_loop(websocket, channel)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Terminal websocket failure for session %s", session_id)
        with contextlib.suppress(Exception):
            await websocket.send_text(f"\r\n[terminal error] {exc}\r\n")
    finally:
        if reader_task:
            reader_task.cancel()
            with contextlib.suppress(Exception):
                await reader_task
        if channel:
            with contextlib.suppress(Exception):
                ssh_manager.close_terminal_channel(channel)
        with contextlib.suppress(Exception):
            await websocket.close()


async def _terminal_reader_loop(websocket: WebSocket, channel) -> None:
    while True:
        if channel.closed:
            break
        if channel.recv_ready():
            data = await asyncio.to_thread(channel.recv, 32768)
            if not data:
                break
            try:
                await websocket.send_text(data.decode("utf-8", errors="replace"))
            except Exception:
                break
            continue
        await asyncio.sleep(0.02)


async def _terminal_writer_loop(websocket: WebSocket, channel) -> None:
    while True:
        try:
            message = await websocket.receive_text()
        except WebSocketDisconnect:
            break
        except RuntimeError as exc:
            if "not connected" in str(exc).lower():
                break
            raise
        payload = _parse_terminal_message(message)
        message_type = payload.get("type")
        if message_type == "input":
            data = str(payload.get("data") or "")
            if data:
                await asyncio.to_thread(channel.send, data)
            continue
        if message_type == "resize":
            cols = int(payload.get("cols") or 140)
            rows = int(payload.get("rows") or 42)
            await asyncio.to_thread(
                ssh_manager.resize_terminal_channel,
                channel,
                width=cols,
                height=rows,
            )
            continue
        if message_type == "ping":
            await websocket.send_text("")


def _parse_terminal_message(raw: str) -> dict:
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    # Backward-compatible fallback: treat raw text as terminal input.
    return {"type": "input", "data": raw}


def _int_query(websocket: WebSocket, key: str, default: int) -> int:
    raw = websocket.query_params.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _websocket_authorized(websocket: WebSocket) -> bool:
    token = os.environ.get("OPSCORE_API_TOKEN", "")
    if not token:
        return True
    if is_authorized_request(websocket.headers, token):
        return True
    query_token = str(websocket.query_params.get("token") or "")
    return bool(query_token) and hmac.compare_digest(query_token, token)
