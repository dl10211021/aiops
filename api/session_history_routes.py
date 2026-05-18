from fastapi import APIRouter, Query

from api.errors import raise_http_error
from api.response_mappers.session import (
    session_history_cleared_response_kwargs,
    session_history_evidence_response_kwargs,
    session_history_export_response_kwargs,
    session_history_message_deleted_response_kwargs,
    session_history_message_feedback_response_kwargs,
    session_history_message_updated_response_kwargs,
    session_history_response_kwargs,
    session_history_search_response_kwargs,
    session_memory_activity_response_kwargs,
    session_run_learning_candidate_created_response_kwargs,
    session_run_learning_preview_response_kwargs,
    session_run_trace_audit_summary_response_kwargs,
    session_run_trace_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.sessions import (
    SessionMessageFeedbackRequest,
    SessionMessageUpdateRequest,
    SessionRunLearningCandidateRequest,
)
from connections.ssh_manager import ssh_manager
from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    create_session_run_learning_candidate_record,
    delete_session_history_message_record,
    export_session_history_markdown_record,
    find_session_history_evidence_trace,
    get_session_run_learning_preview_record,
    get_session_run_trace_audit_summary_record,
    get_session_run_trace_record,
    get_session_memory_activity_record,
    list_session_history_messages,
    search_session_context_records,
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


@router.get("/session/{session_id}/history/search", response_model=ResponseModel)
async def search_session_history(
    session_id: str,
    query: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=100),
):
    """统一搜索会话消息、工具证据和 Run Trace。"""
    try:
        search = search_session_context_records(session_id, query=query, limit=limit)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_search_response_kwargs(search))


@router.get("/session/{session_id}/history/evidence", response_model=ResponseModel)
async def get_session_history_evidence(
    session_id: str,
    evidence_id: str = "",
    tool_call_id: str = "",
    tool: str = "",
    limit: int = Query(200, ge=1, le=500),
):
    """按证据 ID、工具调用 ID 或工具名定位会话中的单条执行轨迹。"""
    try:
        result = find_session_history_evidence_trace(
            session_id,
            evidence_id=evidence_id,
            tool_call_id=tool_call_id,
            tool=tool,
            limit=limit,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_history_evidence_response_kwargs(result))


@router.get("/session/{session_id}/history/run-trace", response_model=ResponseModel)
async def get_session_run_trace(
    session_id: str,
    limit: int = Query(200, ge=1, le=500),
    run_id: str = "",
):
    """获取会话运行生命周期事件，用于 AIOps Run Trace。"""
    try:
        trace = get_session_run_trace_record(session_id, limit=limit, run_id=run_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_run_trace_response_kwargs(trace["events"], trace["runs"]))


@router.get("/session/{session_id}/history/run-trace/audit-summary", response_model=ResponseModel)
async def get_session_run_trace_audit_summary(
    session_id: str,
    limit: int = Query(200, ge=1, le=500),
    run_id: str = "",
):
    """聚合会话 Run Trace 的 Context/Prompt 审计覆盖情况。"""
    try:
        summary = get_session_run_trace_audit_summary_record(session_id, limit=limit, run_id=run_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_run_trace_audit_summary_response_kwargs(summary))


@router.get("/session/{session_id}/history/run-trace/learning-preview", response_model=ResponseModel)
async def get_session_run_learning_preview(
    session_id: str,
    limit: int = Query(200, ge=1, le=500),
    run_id: str = "",
):
    """从会话 Run Trace 生成只读学习候选预览，不写入记忆。"""
    try:
        preview = get_session_run_learning_preview_record(session_id, limit=limit, run_id=run_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_run_learning_preview_response_kwargs(preview))


@router.post("/session/{session_id}/history/run-trace/learning-candidate", response_model=ResponseModel)
async def create_session_run_learning_candidate(
    session_id: str,
    req: SessionRunLearningCandidateRequest,
):
    """人工将 Run Trace 预览提交到学习候选池。"""
    try:
        result = create_session_run_learning_candidate_record(
            session_id,
            run_id=req.run_id or "",
            actor=req.actor,
            reason=req.reason,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_run_learning_candidate_created_response_kwargs(result))


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
