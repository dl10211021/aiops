from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from core.safety_policy_service import (
    SAFETY_POLICY_TEST_TOOLS,
    build_safety_policy_test_context,
    build_safety_policy_test_tool_args,
)


class SafetyPolicyUpdateRequest(BaseModel):
    policy: dict


class ProviderConfig(BaseModel):
    id: str
    name: str = ""
    protocol: str = "openai"
    base_url: str = ""
    api_key: str = ""
    models: str = ""


class EmbeddingConfigRequest(BaseModel):
    model: str
    dim: int


class AgentRuntimeConfigRequest(BaseModel):
    chat_max_steps: int = Field(80, ge=10, le=200)
    headless_max_steps: int = Field(60, ge=10, le=200)


class AssistantModelConfigRequest(BaseModel):
    main_model_id: str = ""
    enabled: bool = False
    model_id: str = ""
    thinking_mode: str = "high"
    tasks: dict = Field(default_factory=dict)


class NotificationConfigRequest(BaseModel):
    wechat_enabled: bool = True
    wechat_webhook: str = ""
    dingtalk_enabled: bool = True
    dingtalk_webhook: str = ""
    email_enabled: bool = True
    email_address: str = ""
    smtp_server: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_pass: str = ""


class TestNotificationRequest(BaseModel):
    channel: str


class SafetyPolicyTestRequest(BaseModel):
    tool_name: str = Field(default="linux_execute_command", max_length=80)
    command: str | None = Field(default=None, max_length=2000)
    sql: str | None = Field(default=None, max_length=4000)
    method: str | None = Field(default=None, max_length=16)
    path: str | None = Field(default=None, max_length=1200)
    oid: str | None = Field(default=None, max_length=120)
    body: dict | None = None
    allow_modifications: bool = False
    asset_type: str | None = Field(default=None, max_length=80)
    protocol: str | None = Field(default=None, max_length=80)
    host: str | None = Field(default=None, max_length=255)
    trigger_source: str | None = Field(default="chat", max_length=80)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_test_input(self):
        if self.tool_name not in SAFETY_POLICY_TEST_TOOLS:
            raise ValueError("不支持的安全策略测试工具。")
        if self.method and self.method.upper() not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("HTTP 方法只能是 GET、HEAD、POST、PUT、PATCH、DELETE。")
        has_input = any(
            str(value or "").strip()
            for value in (self.command, self.sql, self.method, self.path, self.oid)
        )
        if not has_input:
            raise ValueError("请至少填写命令、SQL、HTTP 方法、API 路径或 OID。")
        return self

    def tool_args(self) -> dict:
        return build_safety_policy_test_tool_args(self)

    def context(self) -> dict:
        return build_safety_policy_test_context(self)
