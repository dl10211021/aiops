from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator


class SessionMessageUpdateRequest(BaseModel):
    content: str = Field(..., min_length=0, max_length=200000)


class SessionMessageFeedbackRequest(BaseModel):
    rating: str = Field(..., pattern="^(up|down)$")
    note: str | None = Field(default=None, max_length=1000)


class SessionProfileGenerateRequest(BaseModel):
    model_name: str | None = None
    include_inspection: bool = True


class SessionWebhookSendRequest(BaseModel):
    webhook_url: str = Field(..., min_length=8, max_length=2048)
    payload_type: str = "profile"  # profile | summary | markdown
    channel: str = "generic"  # generic | wechat | dingtalk
    title: str | None = None
    model_name: str | None = None
    allow_private_targets: bool = False


class SlashCommandPayload(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    label: str = Field(..., min_length=2, max_length=80)
    description: str = Field(default="", max_length=240)
    prompt_template: str = Field(..., min_length=5, max_length=6000)
    category: str = Field(default="自定义", max_length=40)
    scope_type: str = Field(default="global", pattern="^(global|asset_type|protocol|asset)$")
    asset_type: str = Field(default="", max_length=80)
    protocol: str = Field(default="", max_length=80)
    host: str = Field(default="", max_length=255)
    readonly: bool = True
    pinned: bool = False
    enabled: bool = True
    sort_order: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.id and not re.fullmatch(r"[A-Za-z0-9_.:-]+", self.id):
            raise ValueError("快捷命令 ID 只能包含字母、数字、点、冒号、短横线和下划线。")
        if self.scope_type == "asset_type" and not self.asset_type.strip():
            raise ValueError("按系统生效时必须填写资产类型。")
        if self.scope_type == "protocol" and not self.protocol.strip():
            raise ValueError("按协议生效时必须填写协议。")
        if self.scope_type == "asset" and not (self.asset_type.strip() and self.protocol.strip() and self.host.strip()):
            raise ValueError("按单资产生效时必须填写资产类型、协议和主机。")
        return self


class PermissionUpdateRequest(BaseModel):
    allow_modifications: bool


class HeartbeatUpdateRequest(BaseModel):
    heartbeat_enabled: bool
    master_interval: int | None = None


class SkillsUpdateRequest(BaseModel):
    active_skills: list[str]


class SessionGroupUpdateRequest(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=80)


class SessionMetadataUpdateRequest(BaseModel):
    remark: str | None = Field(default=None, max_length=200)
    group_name: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = Field(default=None, max_length=40)
