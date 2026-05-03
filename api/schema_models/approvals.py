from __future__ import annotations

from pydantic import BaseModel, Field


class ToolApprovalRequest(BaseModel):
    tool_call_id: str
    approved: bool
    auto_approve_all: bool = False
    operator: str | None = "user"
    note: str | None = ""


class UserInteractionResponseRequest(BaseModel):
    request_id: str = Field(..., min_length=1, max_length=200)
    value: str | None = Field(default="", max_length=4000)
    label: str | None = Field(default="", max_length=200)


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    operator: str | None = "user"
    note: str | None = ""
