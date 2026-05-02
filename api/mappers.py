from __future__ import annotations

from typing import Any

from api.schemas import SessionWebhookSendRequest


def session_webhook_delivery_kwargs(req: SessionWebhookSendRequest) -> dict[str, Any]:
    return {
        "webhook_url": req.webhook_url,
        "payload_type": req.payload_type,
        "channel": req.channel,
        "title": req.title,
        "model_name": req.model_name,
        "allow_private_targets": req.allow_private_targets,
    }
