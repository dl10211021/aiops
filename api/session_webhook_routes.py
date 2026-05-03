from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.session import (
    session_webhook_delivery_kwargs,
    session_webhook_history_response_kwargs,
    session_webhook_preview_response_kwargs,
    session_webhook_sent_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.sessions import SessionWebhookSendRequest
from connections.ssh_manager import ssh_manager
from core.session_webhook_service import (
    SessionWebhookServiceError,
    list_session_webhook_delivery_records,
    preview_session_webhook_delivery,
    send_session_webhook_delivery,
)


router = APIRouter()


@router.post("/session/{session_id}/webhook/send", response_model=ResponseModel)
async def send_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """将会话画像、摘要或完整 Markdown 发送到指定 Webhook。"""
    try:
        payload = await send_session_webhook_delivery(
            ssh_manager.active_sessions,
            session_id=session_id,
            **session_webhook_delivery_kwargs(req),
        )
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_webhook_sent_response_kwargs(payload))


@router.post("/session/{session_id}/webhook/preview", response_model=ResponseModel)
async def preview_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """发送前预览会话 Webhook 目标和载荷，不实际发出请求。"""
    try:
        payload = await preview_session_webhook_delivery(
            ssh_manager.active_sessions,
            session_id=session_id,
            **session_webhook_delivery_kwargs(req),
        )
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_webhook_preview_response_kwargs(payload))


@router.get("/session/{session_id}/webhook/history", response_model=ResponseModel)
async def list_session_webhook_history(session_id: str, limit: int = 10):
    """查看当前会话最近 Webhook 发送历史。"""
    try:
        deliveries = await list_session_webhook_delivery_records(session_id, limit)
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_webhook_history_response_kwargs(deliveries))
