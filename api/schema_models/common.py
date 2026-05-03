from __future__ import annotations

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    status: str
    data: dict = Field(default_factory=dict)
    message: str = ""
