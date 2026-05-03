from fastapi import APIRouter, UploadFile, File
from connections.ssh_manager import ssh_manager
from fastapi.responses import StreamingResponse
from core.agent import chat_stream_agent
from api.errors import raise_http_error
from api.mappers import (
    chat_stream_agent_kwargs,
    chat_attachment_preview_response_kwargs,
)
from api.system_info_routes import router as system_info_router
from api.knowledge_routes import router as knowledge_router
from api.alert_routes import router as alert_router
from api.dashboard_routes import router as dashboard_router
from api.protocol_verification_routes import router as protocol_verification_router
from api.notification_routes import router as notification_router
from api.config_routes import router as config_router
from api.approval_routes import router as approval_router
from api.connection_routes import router as connection_router
from api.skill_routes import router as skill_router
from api.asset_routes import router as asset_router
from api.session_runtime_routes import router as session_runtime_router
from api.session_history_routes import router as session_history_router
from api.session_profile_routes import router as session_profile_router
from api.session_webhook_routes import router as session_webhook_router
from api.custom_command_routes import router as custom_command_router
from api.inspection_template_routes import router as inspection_template_router
from api.inspection_job_routes import router as inspection_job_router
from api.inspection_run_routes import router as inspection_run_router
from core.chat_attachments import (
    CHAT_ATTACHMENT_MAX_SIZE,
    ChatAttachmentError,
    build_chat_attachment_preview,
)
from core.chat_session_service import (
    ChatSessionServiceError,
    start_session_chat_run,
)
from api.schemas import (
    ChatRequest,
    ResponseModel,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(system_info_router)
router.include_router(knowledge_router)
router.include_router(alert_router)
router.include_router(dashboard_router)
router.include_router(protocol_verification_router)
router.include_router(notification_router)
router.include_router(config_router)
router.include_router(approval_router)
router.include_router(connection_router)
router.include_router(skill_router)
router.include_router(asset_router)
router.include_router(session_runtime_router)
router.include_router(session_history_router)
router.include_router(session_profile_router)
router.include_router(session_webhook_router)
router.include_router(custom_command_router)
router.include_router(inspection_template_router)
router.include_router(inspection_job_router)
router.include_router(inspection_run_router)


def _preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    try:
        return build_chat_attachment_preview(filename, content_type, content)
    except ChatAttachmentError as exc:
        raise_http_error(exc)


# ----------------- 路由接口 -----------------


@router.post("/chat")
async def ai_chat_with_system(req: ChatRequest):
    """
    【新功能】：前端流式对话接口 (Server-Sent Events)
    不再傻等 20 秒，实时推送 AI 的思维链、动作和总结。
    """
    logger.info(
        f"AI Stream Chat received: '{req.message}' for session {req.session_id} using model [{req.model_name}]"
    )

    try:
        run = start_session_chat_run(
            ssh_manager.active_sessions,
            req.session_id,
            lambda: chat_stream_agent(**chat_stream_agent_kwargs(req)),
        )
    except ChatSessionServiceError as exc:
        raise_http_error(exc)
    return StreamingResponse(run.subscribe(), media_type="text/event-stream")


@router.post("/chat/attachments/preview", response_model=ResponseModel)
async def preview_chat_attachment(file: UploadFile = File(...)):
    """Parse a small document for one-off chat context without ingesting it into the KB."""
    content = await file.read(CHAT_ATTACHMENT_MAX_SIZE + 1)
    attachment = _preview_attachment_content(
        file.filename or "",
        file.content_type or "application/octet-stream",
        content,
    )
    return ResponseModel(**chat_attachment_preview_response_kwargs(attachment))

