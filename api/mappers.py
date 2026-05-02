from __future__ import annotations

from typing import Any

from api.schemas import ChatRequest, SessionWebhookSendRequest


def chat_stream_agent_kwargs(req: ChatRequest) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "user_message": req.message,
        "user_display_message": req.display_message,
        "model_name": req.model_name,
        "thinking_mode": req.thinking_mode or "off",
        "user_attachments": req.attachments,
    }


def session_webhook_delivery_kwargs(req: SessionWebhookSendRequest) -> dict[str, Any]:
    return {
        "webhook_url": req.webhook_url,
        "payload_type": req.payload_type,
        "channel": req.channel,
        "title": req.title,
        "model_name": req.model_name,
        "allow_private_targets": req.allow_private_targets,
    }


def tool_approval_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    response = {
        "status": "success",
        "message": result["message"],
    }
    if result["include_approval"]:
        response["data"] = {"approval": result["approval"]}
    return response
