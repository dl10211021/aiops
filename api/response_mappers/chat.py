from __future__ import annotations

from typing import Any

from api.schema_models.chat import ChatRequest


def chat_stream_agent_kwargs(req: ChatRequest) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "user_message": req.message,
        "user_display_message": req.display_message,
        "model_name": req.model_name,
        "thinking_mode": req.thinking_mode or "off",
        "user_attachments": req.attachments,
    }


def chat_attachment_preview_response_kwargs(attachment: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"attachment": attachment},
    }


def chat_stop_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "已发送中止信号。",
    }
