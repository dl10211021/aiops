from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from core.chat_attachments import normalize_chat_attachments


class ChatRequest(BaseModel):
    session_id: str
    message: str
    display_message: str | None = None
    model_name: str | None = None
    thinking_mode: str | None = "off"
    attachments: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attachments(self):
        self.attachments = normalize_chat_attachments(self.attachments)
        return self
