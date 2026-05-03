from __future__ import annotations

from pydantic import BaseModel


class AlertEventUpdateRequest(BaseModel):
    status: str | None = None
    assignee: str | None = None
    note: str | None = None
