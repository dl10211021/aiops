from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.session import (
    session_history_cleared_response_kwargs,
    session_history_export_response_kwargs,
    session_history_message_deleted_response_kwargs,
    session_history_message_feedback_response_kwargs,
    session_history_message_updated_response_kwargs,
    session_history_response_kwargs,
    session_memory_activity_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.sessions import SessionMessageFeedbackRequest, SessionMessageUpdateRequest
from connections.ssh_manager import ssh_manager
from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    delete_session_history_message_record,
    export_session_history_markdown_record,
    get_session_memory_activity_record,
    list_session_history_messages,
    update_session_history_message_feedback_record,
    update_session_history_message_record,
)


router = APIRouter()


@router.get("/session/{session_id}/history", response_model=ResponseModel)
async def get_session_history(session_id: str, limit: int | None = None):
    """【新功能】获取会话的历史消息记录，用于前端恢复"""
    try:
        messages = list_session_history_messages(session_id, limit=limit)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_response_kwargs(messages))


@router.delete("/session/{session_id}/history", response_model=ResponseModel)
async def delete_session_history(session_id: str):
    """【新功能】清空会话的聊天记录"""
    try:
        clear_session_history_messages(session_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_cleared_response_kwargs())


@router.patch("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def update_session_history_message(
    session_id: str,
    message_id: int,
    req: SessionMessageUpdateRequest,
):
    """修改单条用户可见会话消息。"""
    try:
        message = update_session_history_message_record(
            session_id,
            message_id,
            req.content,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_message_updated_response_kwargs(message))


@router.post("/session/{session_id}/history/{message_id}/feedback", response_model=ResponseModel)
async def feedback_session_history_message(
    session_id: str,
    message_id: int,
    req: SessionMessageFeedbackRequest,
):
    """记录 AI 输出的用户反馈，并写入单独反馈记忆。"""
    try:
        message = update_session_history_message_feedback_record(
            session_id,
            message_id,
            req.rating,
            req.note,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_message_feedback_response_kwargs(message))


@router.delete("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def delete_session_history_message(session_id: str, message_id: int):
    """删除单条用户可见会话消息。"""
    try:
        delete_session_history_message_record(session_id, message_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_message_deleted_response_kwargs())


@router.get("/session/{session_id}/export", response_model=ResponseModel)
async def export_session_history(session_id: str):
    """【#22 新功能】服务端导出会话历史为 Markdown 格式"""
    try:
        markdown = export_session_history_markdown_record(
            ssh_manager.active_sessions,
            session_id,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_export_response_kwargs(markdown))


@router.get("/session/{session_id}/memory/activity", response_model=ResponseModel)
async def get_session_memory_activity(session_id: str):
    """获取当前会话关联的记忆引用、反馈和待确认冲突。"""
    try:
        activity = get_session_memory_activity_record(session_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_memory_activity_response_kwargs(activity))
