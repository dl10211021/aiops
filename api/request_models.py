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


class PermissionUpdateRequest(BaseModel):
    allow_modifications: bool


class HeartbeatUpdateRequest(BaseModel):
    heartbeat_enabled: bool
    master_interval: int | None = None


class SkillsUpdateRequest(BaseModel):
    active_skills: list[str]


class SessionGroupUpdateRequest(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=80)


class MigrateRequest(BaseModel):
    source_path: str
    target_dir_name: str


class SkillRollbackRequest(BaseModel):
    file_name: str = "SKILL.md"
    version_id: str
    approval_id: str | None = None


class SkillValidationRequest(BaseModel):
    skill_id: str
    file_name: str = "SKILL.md"
    content: str


class CreateSkillRequest(BaseModel):
    skill_id: str
    description: str
    instructions: str
    script_name: str | None = None
    script_content: str | None = None
    overwrite_existing: bool = False


class CronAddRequest(BaseModel):
    cron_expr: str = "0 9 * * *"
    message: str = "执行每日系统深度体检，生成资源使用率报告并发送到群组。"
    host: str = ""
    username: str = ""
    agent_profile: str = "default"
    password: str | None = None
    private_key_path: str | None = None
    asset_id: int | None = None
    target_scope: str = "asset"
    scope_value: str | None = None
    template_id: str | None = None
    notification_channel: str = "auto"
    retry_count: int = 0
    active_skills: list[str] = Field(default_factory=list)


class BatchAssetImportItem(BaseModel):
    remark: str | None = ""
    host: str
    port: int = 22
    username: str = ""
    password: str | None = ""
    asset_type: str = "ssh"
    protocol: str | None = None
    agent_profile: str = "default"
    extra_args: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=lambda: ["未分组"])


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
