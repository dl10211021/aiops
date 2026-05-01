from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator

from core.asset_protocols import resolve_asset_identity
from core.chat_attachments import normalize_chat_attachments
from core.safety_policy_service import (
    SAFETY_POLICY_TEST_TOOLS,
    build_safety_policy_test_context,
    build_safety_policy_test_tool_args,
)


class ConnectionRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: str | None = None
    private_key_path: str | None = None
    allow_modifications: bool = False
    active_skills: list[str] = Field(default_factory=list)  # 增加用户动态勾选的技能包 ID 列表
    agent_profile: str = "default"  # [OpenClaw] Agent 身份/工作区
    remark: str | None = ""  # [新功能] 连接备注/别名
    asset_type: str = "ssh"  # 资产子类型，如 linux/mysql/zabbix
    protocol: str | None = None  # 登录协议，如 ssh/winrm/mysql/http_api/snmp
    extra_args: dict = Field(default_factory=dict)  # [新功能] 扩展参数，比如 db_name, api_key 等
    tags: list[str] = Field(default_factory=lambda: ["未分组"])  # [新功能] 资产组别

    @model_validator(mode="after")
    def validate_extra_args(self):
        identity = resolve_asset_identity(
            self.asset_type,
            self.protocol,
            self.extra_args,
            self.host,
            self.port,
            self.remark,
        )
        asset_type = identity["asset_type"]
        protocol = identity["protocol"]
        if protocol == "snmp":
            if self.extra_args.get("snmp_version") == "v3":
                auth_protocol = str(self.extra_args.get("v3_auth_protocol") or "none").lower()
                priv_protocol = str(self.extra_args.get("v3_priv_protocol") or "none").lower()
                if auth_protocol not in {"none", "noauth"} and not self.extra_args.get("v3_auth_pass"):
                    raise ValueError("SNMPv3 auth mode requires v3_auth_pass")
                if priv_protocol not in {"none", "nopriv"} and not self.extra_args.get("v3_priv_pass"):
                    raise ValueError(
                        "SNMPv3 privacy mode requires v3_priv_pass"
                    )
        elif asset_type == "k8s":
            if not self.extra_args.get("kubeconfig") and not self.extra_args.get("bearer_token"):
                # Allow API reachability testing without credentials, but execution will
                # still fail clearly if a protected endpoint needs a token.
                pass
        elif protocol == "oracle":
            if not (
                self.extra_args.get("SID")
                or self.extra_args.get("service_name")
                or self.extra_args.get("tns_alias")
                or self.extra_args.get("database")
                or self.extra_args.get("db_name")
            ):
                raise ValueError(
                    "oracle connection requires SID/service_name/tns_alias/database/db_name in extra_args"
                )
        return self

    target_scope: str = "asset"  # 作用域：global, group, asset
    scope_value: str | None = (
        None  # 如果 scope 为 group，则为 tag 名称；如果为 asset，为 host/id；global 为空
    )


class ConnectionInspectionRequest(ConnectionRequest):
    keep_session: bool = False


class CommandRequest(BaseModel):
    session_id: str
    command: str


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


class SessionMessageUpdateRequest(BaseModel):
    content: str = Field(..., min_length=0, max_length=200000)


class ResponseModel(BaseModel):
    status: str
    data: dict = Field(default_factory=dict)
    message: str = ""


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


class AssetPayload(BaseModel):
    remark: str | None = ""
    host: str
    port: int = 22
    username: str = ""
    password: str | None = ""
    asset_type: str = "linux"
    protocol: str | None = None
    agent_profile: str = "default"
    extra_args: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=lambda: ["未分组"])


class InspectionTemplateStepPayload(BaseModel):
    name: str
    title: str | None = None
    tool: str
    command: str | None = ""
    sql: str | None = ""
    path: str | None = ""
    oid: str | None = ""
    method: str | None = "GET"
    timeout: int | None = 15
    args: dict = Field(default_factory=dict)


class InspectionTemplatePayload(BaseModel):
    id: str
    name: str
    asset_type: str = "*"
    protocol: str = "*"
    enabled: bool = True
    steps: list[InspectionTemplateStepPayload]


class AlertEventUpdateRequest(BaseModel):
    status: str | None = None
    assignee: str | None = None
    note: str | None = None


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
