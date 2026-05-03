import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

from api.errors import raise_http_error
from api.mappers import (
    chat_attachment_preview_response_kwargs,
    chat_stream_agent_kwargs,
)
from api.schemas import ChatRequest, ResponseModel
from connections.ssh_manager import ssh_manager
from core.agent import chat_stream_agent
from core.chat_attachments import (
    CHAT_ATTACHMENT_MAX_SIZE,
    ChatAttachmentError,
    build_chat_attachment_preview,
)
from core.chat_session_service import (
    ChatSessionServiceError,
    start_session_chat_run,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    try:
        return build_chat_attachment_preview(filename, content_type, content)
    except ChatAttachmentError as exc:
        raise_http_error(exc)


@router.post("/chat")
async def ai_chat_with_system(req: ChatRequest):
    """
    【新功能】：前端流式对话接口 (Server-Sent Events)
    不再傻等 20 秒，实时推送 AI 的思维链、动作和总结。
    """
    logger.info(
        "AI Stream Chat received: '%s' for session %s using model [%s]",
        req.message,
        req.session_id,
        req.model_name,
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
