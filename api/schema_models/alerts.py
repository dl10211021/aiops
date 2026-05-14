from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AlertEventUpdateRequest(BaseModel):
    status: str | None = None
    assignee: str | None = None
    note: str | None = None


class AlertPolicyUpdateRequest(BaseModel):
    policy: dict[str, Any]


class AlertPolicyTestRequest(BaseModel):
    payload: dict[str, Any]


class AlertWorkflowMessageRequest(BaseModel):
    role: str = "user"
    content: str
