from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from connections.ssh_manager import ssh_manager
from fastapi.responses import StreamingResponse
from core.agent import chat_stream_agent
from core.asset_protocols import (
    API_PROTOCOLS,
    CONTAINER_ASSET_TYPES,
    DB_PROTOCOLS,
    MIDDLEWARE_ASSET_TYPES,
    NETWORK_CLI_ASSET_TYPES,
    SQL_PROTOCOLS,
    STORAGE_ASSET_TYPES,
    get_asset_catalog,
    resolve_asset_identity,
)
from core.connection_errors import classify_connection_error, connection_error_http_status
from core.session_views import build_active_sessions_response
from core.skill_lifecycle import validate_skill_candidate
from core.tool_registry import tool_registry
from core.chat_attachments import (
    ChatAttachmentError,
    normalize_chat_attachments,
    preview_attachment_content,
)
from core.session_webhook import (
    SessionWebhookError,
    build_session_webhook_payload,
    post_webhook,
    validate_webhook_url,
    webhook_payload_preview,
)
from core.dashboard_metrics import (
    build_alert_trend,
    build_dashboard_overview,
    build_risk_ranking,
)
from core.asset_responses import mask_asset_response, mask_asset_responses
from core.asset_catalog_response import build_asset_types_response
from core.notification_config import (
    build_notification_config,
    build_notification_env_values,
)
from core.notification_test import (
    NotificationTestError,
    send_notification_channel_test,
)
from core.session_runtime import (
    SessionRuntimeError,
    drain_all_pending_messages,
    drain_session_pending_messages,
    set_session_group,
    set_session_heartbeat,
    set_session_permission,
    set_session_skills,
)
from core.session_history import (
    build_session_history_markdown as build_session_history_markdown_content,
    clear_session_history as clear_session_history_messages,
    delete_session_message,
    get_user_visible_session_history,
    update_session_message_content,
)

import logging
import asyncio
import os
import json
import re
import time
import zipfile
from pathlib import Path

webhook_locks = {}
logger = logging.getLogger(__name__)
CUSTOM_SKILLS_DIR = Path(__file__).resolve().parent.parent / "my_custom_skills"

router = APIRouter()


def connection_error_response(raw_error, protocol: str = "", context: str = "") -> "ResponseModel":
    error = classify_connection_error(raw_error, protocol, context)
    return ResponseModel(status="error", message=error["message"], data={"error": error})


def raise_connection_error(result: dict, protocol: str = "") -> None:
    if result.get("error_code") and result.get("error_category"):
        error = {
            "code": result.get("error_code"),
            "category": result.get("error_category"),
            "message": result.get("message") or "连接失败",
            "raw_error": result.get("raw_error") or result.get("message") or "",
            "protocol": protocol,
        }
    else:
        error = classify_connection_error(result.get("message") or result.get("error"), protocol)
    raise HTTPException(status_code=connection_error_http_status(error), detail=error)


def update_env_file_values(values: dict[str, str]) -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env_lines: list[str] = []
    if env_path.exists():
        env_lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)

    keys = set(values)
    filtered = [
        line
        for line in env_lines
        if not any(line.startswith(f"{key}=") for key in keys)
    ]
    for key, value in values.items():
        filtered.append(f"{key}={value}\n")
    env_path.write_text("".join(filtered), encoding="utf-8")

HTTP_API_TOOL_PRIORITY = (
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "http_api_request",
)


def resolve_custom_skill_dir(target_dir_name: str) -> Path:
    """Return a normalized custom-skill target directory, rejecting traversal."""
    name = str(target_dir_name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise HTTPException(
            status_code=422,
            detail="target_dir_name 只能包含英文字母、数字、横线和下划线。",
        )

    base = CUSTOM_SKILLS_DIR.resolve()
    target = (base / name).resolve()
    if target.parent != base:
        raise HTTPException(status_code=422, detail="非法技能目标路径。")
    return target


def resolve_custom_skill_file(skill_id: str, file_name: str) -> Path:
    skill_dir = resolve_custom_skill_dir(skill_id)
    safe_file = str(file_name or "").strip()
    if not safe_file or os.path.basename(safe_file) != safe_file:
        raise HTTPException(status_code=422, detail="file_name 只能是文件名，不能包含路径。")
    target = (skill_dir / safe_file).resolve()
    if target.parent != skill_dir.resolve():
        raise HTTPException(status_code=422, detail="非法技能文件路径。")
    return target


def resolve_custom_skill_version_file(skill_id: str, version_id: str) -> Path:
    skill_dir = resolve_custom_skill_dir(skill_id)
    safe_version = str(version_id or "").strip()
    if not safe_version or os.path.basename(safe_version) != safe_version:
        raise HTTPException(status_code=422, detail="version_id 只能是版本文件名。")
    versions_dir = (skill_dir / ".versions").resolve()
    target = (versions_dir / safe_version).resolve()
    if target.parent != versions_dir:
        raise HTTPException(status_code=422, detail="非法版本文件路径。")
    return target


def atomic_replace_bytes(file_path: Path, content: bytes) -> None:
    tmp_path = file_path.with_name(f".{file_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def reject_invalid_skill_candidate(validation: dict) -> None:
    if validation["valid"]:
        return
    detail = "；".join(issue["message"] for issue in validation["issues"])
    raise HTTPException(status_code=422, detail=detail or "技能校验失败。")


# ----------------- 数据模型 -----------------
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


def get_login_protocol(req: ConnectionRequest) -> str:
    return resolve_asset_identity(
        req.asset_type, req.protocol, req.extra_args, req.host, req.port, req.remark
    )["protocol"]


def asset_matches_request(asset: dict, req: ConnectionRequest) -> bool:
    if (
        asset.get("host") != req.host
        or asset.get("port") != req.port
        or asset.get("username") != req.username
    ):
        return False
    asset_identity = resolve_asset_identity(
        asset.get("asset_type"),
        asset.get("protocol"),
        asset.get("extra_args", {}),
        asset.get("host"),
        asset.get("port"),
        asset.get("remark"),
    )
    req_identity = resolve_asset_identity(
        req.asset_type, req.protocol, req.extra_args, req.host, req.port, req.remark
    )
    return (
        asset_identity["asset_type"] == req_identity["asset_type"]
        and asset_identity["protocol"] == req_identity["protocol"]
    )


class CommandRequest(BaseModel):
    session_id: str
    command: str


def _normalize_chat_attachments(attachments: list[dict]) -> list[dict]:
    return normalize_chat_attachments(attachments)


class ChatRequest(BaseModel):
    session_id: str
    message: str
    display_message: Optional[str] = None
    model_name: Optional[str] = None
    thinking_mode: Optional[str] = "off"
    attachments: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attachments(self):
        self.attachments = _normalize_chat_attachments(self.attachments)
        return self


class SessionMessageUpdateRequest(BaseModel):
    content: str = Field(..., min_length=0, max_length=200000)


class ResponseModel(BaseModel):
    status: str
    data: dict = Field(default_factory=dict)
    message: str = ""


class SessionProfileGenerateRequest(BaseModel):
    model_name: Optional[str] = None
    include_inspection: bool = True


class SessionWebhookSendRequest(BaseModel):
    webhook_url: str = Field(..., min_length=8, max_length=2048)
    payload_type: str = "profile"  # profile | summary | markdown
    channel: str = "generic"  # generic | wechat | dingtalk
    title: Optional[str] = None
    model_name: Optional[str] = None
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


def _preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    try:
        return preview_attachment_content(filename, content_type, content)
    except ChatAttachmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


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


def _legacy_execute_tool_call(identity: dict, command: str) -> tuple[str, dict]:
    """Map legacy /execute command text to the protocol-native tool call."""
    protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    command = str(command or "").strip()

    if protocol == "ssh" and asset_type in NETWORK_CLI_ASSET_TYPES:
        return "network_cli_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in CONTAINER_ASSET_TYPES:
        return "container_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in MIDDLEWARE_ASSET_TYPES:
        return "middleware_execute_command", {"command": command}
    if protocol == "ssh" and asset_type in STORAGE_ASSET_TYPES:
        return "storage_execute_command", {"command": command}
    if protocol == "ssh":
        return "linux_execute_command", {"command": command}
    if protocol == "winrm":
        return "winrm_execute_command", {"command": command}
    if protocol in SQL_PROTOCOLS:
        return "db_execute_query", {"sql": command}
    if protocol == "redis":
        return "redis_execute_command", {"command": command}
    if protocol == "mongodb":
        try:
            parsed = json.loads(command)
        except Exception:
            parsed = {"collection": command}
        if not isinstance(parsed, dict):
            parsed = {"collection": command}
        return "mongodb_find", {
            "database": parsed.get("database"),
            "collection": parsed.get("collection") or parsed.get("coll") or command,
            "filter": parsed.get("filter") or {},
            "projection": parsed.get("projection"),
            "limit": parsed.get("limit") or 100,
        }
    if protocol in API_PROTOCOLS:
        method = "GET"
        path = command or "/"
        parts = command.split(maxsplit=1)
        if parts and parts[0].upper() in {"GET", "HEAD", "POST"}:
            method = parts[0].upper()
            path = parts[1] if len(parts) > 1 else "/"
        active_tools = {
            tool.name
            for tool in tool_registry.available(
                {
                    "target_scope": "asset",
                    "asset_type": asset_type,
                    "protocol": protocol,
                    "extra_args": identity.get("extra_args") or {},
                }
            )
        }
        tool_name = next((candidate for candidate in HTTP_API_TOOL_PRIORITY if candidate in active_tools), "http_api_request")
        return tool_name, {"method": method, "path": path}
    if protocol == "snmp":
        return "snmp_get", {"oid": command}

    raise HTTPException(
        status_code=400,
        detail=f"/execute 不支持 {asset_type}/{protocol}；请使用聊天会话原生工具或巡检接口。",
    )


# ----------------- 路由接口 -----------------


@router.post("/chat")
async def ai_chat_with_system(req: ChatRequest):
    """
    【新功能】：前端流式对话接口 (Server-Sent Events)
    不再傻等 20 秒，实时推送 AI 的思维链、动作和总结。
    """
    logger.info(
        f"AI Stream Chat received: '{req.message}' for session {req.session_id} using model [{req.model_name}]"
    )

    # 验证 session 有效性
    if req.session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=401, detail="会话已过期或不存在，请重新连接")

    import time

    ssh_manager.active_sessions[req.session_id]["info"]["last_active"] = time.time()

    from core.chat_runs import start_chat_run

    run = start_chat_run(
        req.session_id,
        lambda: chat_stream_agent(
            session_id=req.session_id,
            user_message=req.message,
            user_display_message=req.display_message,
            model_name=req.model_name,
            thinking_mode=req.thinking_mode or "off",
            user_attachments=req.attachments,
        ),
    )
    return StreamingResponse(run.subscribe(), media_type="text/event-stream")


@router.post("/chat/attachments/preview", response_model=ResponseModel)
async def preview_chat_attachment(file: UploadFile = File(...)):
    """Parse a small document for one-off chat context without ingesting it into the KB."""
    original_name = os.path.basename(file.filename or "")
    if not original_name:
        raise HTTPException(status_code=422, detail="附件文件名不能为空。")
    max_bytes = 10 * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="单个会话附件不能超过 10MB。")
    try:
        attachment = _preview_attachment_content(
            original_name,
            file.content_type or "application/octet-stream",
            content,
        )
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="Office 文件结构无效，无法解析。") from exc
    return ResponseModel(status="success", data={"attachment": attachment})


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


@router.post("/session/{session_id}/approve", response_model=ResponseModel)
async def approve_tool_call(session_id: str, req: ToolApprovalRequest):
    """【新功能】用户确认是否允许 AI 执行敏感指令"""
    from core.dispatcher import dispatcher
    from core.approval_queue import resolve_approval_request
    from connections.ssh_manager import ssh_manager

    if req.auto_approve_all:
        if session_id in ssh_manager.active_sessions:
            ssh_manager.active_sessions[session_id]["info"]["auto_approve_all"] = True
            logger.info(f"Session {session_id} set to auto-approve all tools.")

    future = dispatcher.pending_approvals.get(req.tool_call_id)
    if future and not future.done():
        future.set_result(req.approved)
        try:
            resolve_approval_request(
                req.tool_call_id,
                approved=req.approved,
                operator=req.operator or "user",
                note=req.note or "",
            )
        except KeyError:
            pass
        return ResponseModel(status="success", message="Approval action submitted.")

    try:
        approval = resolve_approval_request(
            req.tool_call_id,
            approved=req.approved,
            operator=req.operator or "user",
            note=req.note or "",
        )
        return ResponseModel(
            status="success",
            message="Approval action recorded.",
            data={"approval": approval},
        )
    except KeyError:
        pass

    raise HTTPException(
        status_code=404,
        detail="Pending tool call not found or already processed.",
    )


@router.post("/session/{session_id}/interaction", response_model=ResponseModel)
async def respond_user_interaction(session_id: str, req: UserInteractionResponseRequest):
    """提交前台聊天中的文本、密码或选项交互响应。"""
    from core.dispatcher import dispatcher

    entry = dispatcher.pending_interactions.get(req.request_id)
    future = entry.get("future") if isinstance(entry, dict) else entry
    expected_session_id = entry.get("session_id") if isinstance(entry, dict) else None
    if expected_session_id and expected_session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail="交互请求不存在、已提交或已超时。",
        )
    if future and not future.done():
        future.set_result({"value": req.value or "", "label": req.label or ""})
        return ResponseModel(status="success", message="交互输入已提交。")

    raise HTTPException(
        status_code=404,
        detail="交互请求不存在、已提交或已超时。",
    )


@router.get("/approvals", response_model=ResponseModel)
async def list_approval_requests(status: str | None = None, limit: int = 100):
    """查询高危工具调用审批队列。"""
    from core.approval_queue import list_approval_requests

    return ResponseModel(
        status="success",
        data={"approvals": list_approval_requests(status=status, limit=limit)},
    )


@router.get("/approvals/{approval_id}", response_model=ResponseModel)
async def get_approval_request(approval_id: str):
    """查询单个审批请求。"""
    from core.approval_queue import get_approval_request

    approval = get_approval_request(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return ResponseModel(status="success", data={"approval": approval})


@router.post("/approvals/{approval_id}/decision", response_model=ResponseModel)
async def decide_approval_request(approval_id: str, req: ApprovalDecisionRequest):
    """审批或拒绝高危工具调用，并写入审计状态。"""
    from core.approval_queue import resolve_approval_request
    from core.dispatcher import dispatcher

    future = dispatcher.pending_approvals.get(approval_id)
    if future and not future.done():
        future.set_result(req.approved)
    try:
        approval = resolve_approval_request(
            approval_id,
            approved=req.approved,
            operator=req.operator or "user",
            note=req.note or "",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return ResponseModel(status="success", message="审批已处理", data={"approval": approval})


@router.post("/approvals/{approval_id}/execute", response_model=ResponseModel)
async def execute_approval_request(approval_id: str):
    """执行已经批准且支持后续执行的审批请求。"""
    from core.approval_queue import get_approval_request as load_approval_request

    approval = load_approval_request(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    if approval.get("status") != "approved":
        raise HTTPException(status_code=409, detail="审批尚未批准，不能执行。")
    if approval.get("execution"):
        raise HTTPException(status_code=409, detail="该审批已经执行过。")
    if approval.get("tool_name") != "rollback_skill":
        raise HTTPException(status_code=422, detail="该审批类型暂不支持直接执行。")

    args = approval.get("args") or {}
    skill_id = str(args.get("skill_id") or "").strip()
    file_name = str(args.get("file_name") or "").strip()
    version_id = str(args.get("version_id") or "").strip()
    if not skill_id or not file_name or not version_id:
        raise HTTPException(status_code=422, detail="审批参数不完整，无法执行技能回滚。")

    response = await rollback_skill_version(
        skill_id,
        SkillRollbackRequest(
            file_name=file_name,
            version_id=version_id,
            approval_id=approval_id,
        ),
    )
    executed_approval = load_approval_request(approval_id)
    return ResponseModel(
        status=response.status,
        message=response.message or "审批动作已执行。",
        data={
            "approval": executed_approval or approval,
            "result": response.data,
        },
    )


@router.post("/session/{session_id}/stop", response_model=ResponseModel)
async def stop_chat_session(session_id: str):
    """【新功能】终止当前会话中正在生成的长流响应/执行任务"""
    from core.agent import cancel_flags

    cancel_flags[session_id] = True
    return ResponseModel(status="success", message="已发送中止信号。")


def get_restored_args(req: ConnectionRequest) -> dict:
    """如果 req 中包含被掩码的 extra_args，则从持久化存储中找回真实值，返回一个新的字典"""
    if not hasattr(req, "extra_args") or not req.extra_args:
        return {}
    has_mask = any(v == "********" for v in req.extra_args.values())
    if not has_mask:
        return req.extra_args

    restored = dict(req.extra_args)
    from core.memory import memory_db

    assets = memory_db.get_all_assets()
    for a in assets:
        if asset_matches_request(a, req):
            db_args = a.get("extra_args", {})
            for k, v in restored.items():
                if v == "********" and k in db_args:
                    restored[k] = db_args[k]
            break
    return restored


def get_restored_password(req: ConnectionRequest) -> str | None:
    """如果前端传回密码掩码，则从持久化资产中恢复真实密码。"""
    if req.password != "********":
        return req.password

    from core.memory import memory_db

    assets = memory_db.get_all_assets()
    for a in assets:
        if asset_matches_request(a, req):
            return a.get("password")
    return None


@router.post("/connect/test", response_model=ResponseModel)
async def test_connection(req: ConnectionRequest):
    import asyncio
    import os

    if req.target_scope == "global":
        return ResponseModel(
            status="success",
            message="[OK] 全局总控会话无需连接单台资产，可直接创建。",
        )

    restored_args = get_restored_args(req)
    # 重新构建请求对象以触发 Pydantic 验证
    req = ConnectionRequest(**{**req.model_dump(), "extra_args": restored_args})
    restored_password = get_restored_password(req)
    identity = resolve_asset_identity(
        req.asset_type, req.protocol, req.extra_args, req.host, req.port, req.remark
    )
    login_protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    extra_args = identity["extra_args"]

    # SSH Test
    if login_protocol == "ssh":

        key_path = (
            req.private_key_path
            if req.private_key_path
            and req.private_key_path.strip().lower() not in ("string", "")
            else None
        )

        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            await asyncio.to_thread(
                client.connect,
                hostname=req.host,
                port=req.port,
                username=req.username,
                password=restored_password,
                key_filename=key_path,
                timeout=5,
            )
            client.close()
            return ResponseModel(
                status="success",
                message="[OK] SSH Connection Successful! Credentials are valid.",
            )
        except Exception as e:
            return connection_error_response(e, "ssh")

    if login_protocol == "winrm":
        from connections.winrm_manager import winrm_executor

        res = await asyncio.to_thread(
            winrm_executor.execute_command,
            host=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            command="$PSVersionTable.PSVersion.ToString()",
            extra_args=req.extra_args,
        )
        if res.get("success"):
            return ResponseModel(
                status="success",
                message="[OK] WinRM Connection Successful! Credentials are valid.",
            )
        return connection_error_response(
            res.get("error") or res.get("output"),
            "winrm",
            str(res.get("error_type") or ""),
        )

    # Database Test
    requested_db_type = req.extra_args.get("db_type") if req.extra_args else None
    if login_protocol in SQL_PROTOCOLS or requested_db_type in SQL_PROTOCOLS:
        from connections.db_manager import db_executor, get_database_operation_profile

        db_type = req.extra_args.get("db_type") or login_protocol or "mysql"
        database = (
            req.extra_args.get("SID")
            or req.extra_args.get("service_name")
            or req.extra_args.get("database")
            or req.extra_args.get("db_name")
            or ""
        )
        sql = get_database_operation_profile(db_type).get("test_statement") or (
            "SELECT 1 FROM DUAL" if db_type == "oracle" else "SELECT 1"
        )

        res_str = await asyncio.to_thread(
            db_executor.execute_query,
            db_type,
            req.host,
            req.port,
            req.username,
            restored_password,
            database,
            sql,
            req.extra_args,
        )
        import json

        res = json.loads(res_str)
        if res.get("success"):
            return ResponseModel(
                status="success",
                message=f"[OK] Database ({db_type.upper()}) Connection Successful!",
            )
        else:
            return connection_error_response(res.get("error"), db_type)

    if login_protocol == "redis" or requested_db_type == "redis":
        from connections.datastore_manager import redis_executor

        res = await asyncio.to_thread(
            redis_executor.execute_command,
            host=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            command="PING",
            extra_args=req.extra_args,
        )
        if res.get("success"):
            return ResponseModel(status="success", message="[OK] Redis Connection Successful!")
        return connection_error_response(res.get("error"), "redis")

    if login_protocol == "memcached" or requested_db_type == "memcached":
        from connections.datastore_manager import memcached_executor

        res = await asyncio.to_thread(
            memcached_executor.execute_command,
            host=req.host,
            port=req.port,
            command="version",
            extra_args=req.extra_args,
        )
        if res.get("success"):
            return ResponseModel(status="success", message="[OK] Memcached Connection Successful!")
        return connection_error_response(res.get("error"), "memcached")

    if login_protocol == "mongodb" or requested_db_type == "mongodb":
        from connections.datastore_manager import mongo_executor

        database = req.extra_args.get("database") or req.extra_args.get("db_name") or "admin"
        res = await asyncio.to_thread(
            mongo_executor.find,
            host=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            database=database,
            collection=str(req.extra_args.get("test_collection") or "system.version"),
            filter_doc={},
            limit=1,
            extra_args=req.extra_args,
        )
        if res.get("success"):
            return ResponseModel(status="success", message="[OK] MongoDB Connection Successful!")
        return connection_error_response(res.get("error"), "mongodb")

    # API Test
    if login_protocol in API_PROTOCOLS or login_protocol == "snmp":
        import socket
        from connections.http_api_manager import build_base_url
        from urllib.parse import urlparse

        try:
            if login_protocol in API_PROTOCOLS:
                parsed = urlparse(build_base_url(req.host, req.port, req.extra_args))
                host = parsed.hostname or req.host
                port = parsed.port or req.port
            else:
                host = req.host
                port = req.port
            with socket.create_connection((host, port), timeout=3):
                pass
            return ResponseModel(
                status="success",
                message=f"[OK] Port {port} is reachable. (Auth testing deferred to execution agent)",
            )
        except Exception as e:
            return connection_error_response(e, login_protocol, "tcp connect")

    # Virtual Test: Ping
    try:
        import subprocess

        cmd = (
            ["ping", "-n", "1", "-w", "1000", req.host]
            if os.name == "nt"
            else ["ping", "-c", "1", "-W", "1", req.host]
        )
        res = await asyncio.to_thread(subprocess.run, cmd, capture_output=True)
        if res.returncode == 0:
            return ResponseModel(
                status="success",
                message="[OK] ICMP Ping Successful! Target is reachable.",
            )
        else:
            return ResponseModel(
                status="success",
                message="[WARN] Ping failed (timeout or blocked). Virtual credentials saved.",
            )
    except Exception:
        return ResponseModel(
            status="success", message="[OK] Virtual credentials saved."
        )


@router.post("/connect/inspect", response_model=ResponseModel)
async def inspect_connection(req: ConnectionInspectionRequest):
    """临时建立会话并执行只读巡检，默认巡检后自动断开。"""
    from core.session_inspector import inspect_session

    if req.target_scope == "global":
        return ResponseModel(
            status="success",
            message="全局总控会话检查完成。",
            data={
                "session_id": None,
                "kept_session": False,
                "inspection": {
                    "status": "success",
                    "supported": True,
                    "asset_type": "virtual",
                    "protocol": "virtual",
                    "profile": "global",
                    "summary": "全局总控会话无需单资产连通性巡检；创建后可使用 list_active_sessions、dispatch_sub_agents、search_assets_by_tag 等编排工具。",
                    "checks": [],
                },
            },
        )

    restored_args = get_restored_args(req)
    req = ConnectionInspectionRequest(**{**req.model_dump(), "extra_args": restored_args})
    restored_password = get_restored_password(req)
    identity = resolve_asset_identity(
        req.asset_type, req.protocol, req.extra_args, req.host, req.port, req.remark
    )
    login_protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    extra_args = identity["extra_args"]

    key_path = req.private_key_path
    if key_path and key_path.strip().lower() in ("string", ""):
        key_path = None

    result = await asyncio.to_thread(
        ssh_manager.connect,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        key_filename=key_path,
        allow_modifications=False,
        active_skills=req.active_skills,
        agent_profile=req.agent_profile,
        remark=req.remark or "巡检测试会话",
        asset_type=asset_type,
        protocol=login_protocol,
        extra_args=extra_args,
        tags=req.tags,
        target_scope=req.target_scope,
        scope_value=req.scope_value,
    )

    if not result.get("success"):
        if result.get("error_code") and result.get("error_category"):
            error = {
                "code": result.get("error_code"),
                "category": result.get("error_category"),
                "message": result.get("message", "连接失败"),
                "raw_error": result.get("raw_error") or result.get("message", ""),
                "protocol": login_protocol,
            }
            return ResponseModel(status="error", message=error["message"], data={"error": error})
        return connection_error_response(result.get("message", "连接失败"), login_protocol)

    session_id = result["session_id"]
    try:
        report = await inspect_session(session_id)
    finally:
        if not req.keep_session:
            await asyncio.to_thread(ssh_manager.disconnect, session_id)

    return ResponseModel(
        status="success" if report.get("status") in {"success", "warning"} else report.get("status", "error"),
        message=report.get("summary") or report.get("message", ""),
        data={
            "session_id": session_id if req.keep_session else None,
            "kept_session": req.keep_session,
            "inspection": report,
        },
    )


@router.post("/connect", response_model=ResponseModel)
async def create_ssh_connection(req: ConnectionRequest):
    """建立与远程系统的会话 (支持 SSH长连接 或 虚拟凭据会话)"""

    if req.target_scope == "global":
        result = await asyncio.to_thread(
            ssh_manager.connect_local,
            agent_profile=req.agent_profile,
            active_skills=req.active_skills,
            remark=req.remark or "全局总控",
            allow_modifications=req.allow_modifications,
            tags=req.tags or ["全局会话"],
            target_scope="global",
            scope_value=req.scope_value,
        )
        return ResponseModel(
            status="success",
            message="Global Session Established",
            data={"session_id": result["session_id"]},
        )

    restored_args = get_restored_args(req)
    req = ConnectionRequest(**{**req.model_dump(), "extra_args": restored_args})
    restored_password = get_restored_password(req)
    identity = resolve_asset_identity(
        req.asset_type, req.protocol, req.extra_args, req.host, req.port, req.remark
    )
    login_protocol = identity["protocol"]
    asset_type = identity["asset_type"]
    extra_args = identity["extra_args"]

    logger.info(
        f"API called: Connect to {req.host} as {asset_type}/{login_protocol} with profile {req.agent_profile}, remark: {req.remark}"
    )

    key_path = req.private_key_path
    if key_path and key_path.strip().lower() in ("string", ""):
        key_path = None

    # 解决同步方法卡死 FastAPI 问题，将其投递到线程池
    result = await asyncio.to_thread(
        ssh_manager.connect,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        key_filename=key_path,
        allow_modifications=req.allow_modifications,
        active_skills=req.active_skills,  # 透传给底层会话
        agent_profile=req.agent_profile,  # 透传 Agent 身份
        remark=req.remark,  # 透传备注
        asset_type=asset_type,  # 资产子类型
        protocol=login_protocol,  # 登录协议
        extra_args=extra_args,  # 透传扩展凭证 (API Key, DB Name 等)
        tags=req.tags,  # 传递分组标签
        target_scope=req.target_scope,
        scope_value=req.scope_value,
    )

    if result["success"]:
        # 将连接成功的资产信息自动沉淀到 SQLite 数据库中，实现“通讯录”功能
        from core.memory import memory_db

        memory_db.save_asset(
            remark=req.remark,
            host=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            asset_type=asset_type,
            protocol=login_protocol,
            agent_profile=req.agent_profile,
            extra_args=extra_args,
            skills=req.active_skills,
            tags=req.tags,
        )

    if not result["success"]:
        raise_connection_error(result, login_protocol)

    return ResponseModel(
        status="success",
        message="Session Established",
        data={"session_id": result["session_id"]},
    )


@router.post("/execute", response_model=ResponseModel)
async def execute_remote_command(req: CommandRequest):
    """
    大模型使用的底层“Skill”核心：
    在已建立的 Session 中下发指令（如 uptime, ps aux）。
    """
    logger.info(f"API called: Executing legacy command on session {req.session_id}")

    if req.session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    from core.dispatcher import dispatcher

    info = ssh_manager.active_sessions[req.session_id]["info"]
    identity = resolve_asset_identity(
        info.get("asset_type"),
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    context = {
        **info,
        "session_id": req.session_id,
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "extra_args": identity["extra_args"],
    }
    tool_name, tool_args = _legacy_execute_tool_call(identity, req.command)
    needs_approval, approval_reason = dispatcher.check_approval_needed(tool_name, tool_args, context)
    if needs_approval:
        raise HTTPException(
            status_code=409,
            detail=f"该操作需要后端审批：{approval_reason}。请在聊天会话中执行，以便弹出审批确认。",
        )

    result_str = await dispatcher.route_and_execute(
        tool_name, tool_args, context
    )
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"success": False, "error": result_str}

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("reason") or "执行失败")

    return ResponseModel(
        status="success",
        data={
            "output": result.get("output") or result.get("data") or "",
            "has_error": result.get("has_error", False),
            "exit_status": result.get("exit_status", 0),
        },
    )


class PermissionUpdateRequest(BaseModel):
    allow_modifications: bool


class HeartbeatUpdateRequest(BaseModel):
    heartbeat_enabled: bool
    master_interval: int | None = None


class SkillsUpdateRequest(BaseModel):
    active_skills: list[str]


class SessionGroupUpdateRequest(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=80)


@router.post("/skills/scan", response_model=ResponseModel)
async def scan_skills():
    """【新功能】前端手动触发扫描本地磁盘目录，热加载新的技能"""
    from core.dispatcher import dispatcher

    dispatcher.refresh_skills(force=True)
    return ResponseModel(status="success", message="扫描完成！本地技能库已更新。")


@router.get("/skills/registry", response_model=ResponseModel)
async def get_skill_registry():
    """【新功能】前端调用，获取所有已安装的技能卡带摘要以及外部市场待下载的卡带"""
    from core.dispatcher import dispatcher

    registry = dispatcher.get_all_registered_skills()
    market = dispatcher.get_market_skills()

    # 合并返回给前端展示，前端根据 is_market 字段区分
    return ResponseModel(status="success", data={"registry": registry + market})


@router.get("/skills/registry/{skill_id}", response_model=ResponseModel)
async def get_skill_detail(skill_id: str):
    """【新功能】前端调用，获取某个特定技能卡带的完整 Markdown 原文"""
    from core.dispatcher import dispatcher

    # 优先找本地的
    if skill_id in dispatcher.skills_registry:
        skill = dispatcher.skills_registry[skill_id]
        return ResponseModel(
            status="success",
            data={
                "instructions": skill["instructions"],
                "source_path": skill["source_path"],
            },
        )

    # 如果本地没有，可能是在查看市场的详情，实时去市场读
    market_skills = dispatcher.get_market_skills()
    for s in market_skills:
        if s["id"] == skill_id:
            with open(
                os.path.join(s["source_path"], "SKILL.md"), "r", encoding="utf-8"
            ) as f:
                content = f.read()
            return ResponseModel(
                status="success",
                data={"instructions": content, "source_path": s["source_path"]},
            )

    raise HTTPException(status_code=404, detail="找不到该技能")


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


@router.post("/skills/create", response_model=ResponseModel)
async def create_skill(req: CreateSkillRequest):
    """【新功能】用户在页面上手动创建新的定制技能卡带"""
    md_content = f"---\nname: {req.skill_id}\ndescription: {req.description}\n---\n\n{req.instructions}\n"
    reject_invalid_skill_candidate(validate_skill_candidate(req.skill_id, "SKILL.md", md_content))
    script_validation = None
    if req.script_name or req.script_content:
        if not req.script_name or req.script_content is None:
            raise HTTPException(status_code=422, detail="脚本名称和脚本内容必须同时提供。")
        script_validation = validate_skill_candidate(req.skill_id, req.script_name, req.script_content)
        reject_invalid_skill_candidate(script_validation)

    CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = resolve_custom_skill_dir(req.skill_id)

    try:
        if dest_path.exists() and not req.overwrite_existing:
            raise HTTPException(
                status_code=409,
                detail=f"该技能包 ID ({req.skill_id}) 已存在，请换一个名称。",
            )
        from core.dispatcher import dispatcher

        backup_paths = []
        if dest_path.exists():
            skill_backup = dispatcher._backup_existing_skill_file(str(dest_path / "SKILL.md"))
            if skill_backup:
                backup_paths.append(skill_backup)
        else:
            dest_path.mkdir()

        atomic_replace_bytes(dest_path / "SKILL.md", md_content.encode("utf-8"))

        # 如果提供了脚本内容，一并写入
        if script_validation:
            script_path = dest_path / script_validation["file_name"]
            script_backup = dispatcher._backup_existing_skill_file(str(script_path))
            if script_backup:
                backup_paths.append(script_backup)
            atomic_replace_bytes(script_path, req.script_content.encode("utf-8"))

        # 通知 Dispatcher 重新加载
        dispatcher.refresh_skills(force=True)

        action = "更新" if req.overwrite_existing else "创建"
        return ResponseModel(
            status="success",
            message=f"定制技能 {req.skill_id} {action}成功，已自动加载就绪！",
            data={
                "skill_id": req.skill_id,
                "skill_path": str(dest_path),
                "backup_paths": backup_paths,
                "updated": bool(req.overwrite_existing),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/skills/validate", response_model=ResponseModel)
async def validate_skill(req: SkillValidationRequest):
    """静态校验技能文件内容，不写文件、不执行脚本。"""
    result = validate_skill_candidate(req.skill_id, req.file_name, req.content)
    return ResponseModel(status="success", data=result)


@router.get("/skills/{skill_id}/versions", response_model=ResponseModel)
async def list_skill_versions(skill_id: str, file_name: str = "SKILL.md"):
    """列出 my_custom_skills 中某个技能文件的可回滚版本。"""
    skill_file = resolve_custom_skill_file(skill_id, file_name)
    versions_dir = skill_file.parent / ".versions"
    if not skill_file.parent.exists():
        raise HTTPException(status_code=404, detail="技能不存在。")

    versions = []
    if versions_dir.exists():
        prefix = f"{skill_file.name}."
        suffix = ".bak"
        for item in versions_dir.iterdir():
            if not item.is_file() or not item.name.startswith(prefix) or not item.name.endswith(suffix):
                continue
            stat = item.stat()
            versions.append(
                {
                    "id": item.name,
                    "file_name": skill_file.name,
                    "size": stat.st_size,
                    "created_at_ts": stat.st_mtime,
                }
            )
    versions.sort(key=lambda item: item["created_at_ts"], reverse=True)
    return ResponseModel(status="success", data={"versions": versions})


@router.post("/skills/{skill_id}/rollback", response_model=ResponseModel)
async def rollback_skill_version(skill_id: str, req: SkillRollbackRequest):
    """将 my_custom_skills 中的技能文件回滚到指定备份版本。"""
    from core.dispatcher import dispatcher
    from core.approval_queue import (
        get_approval_request,
        record_approval_execution,
        record_approval_request,
    )

    target_file = resolve_custom_skill_file(skill_id, req.file_name)
    version_file = resolve_custom_skill_version_file(skill_id, req.version_id)
    if not target_file.parent.exists():
        raise HTTPException(status_code=404, detail="技能不存在。")
    if not version_file.is_file():
        raise HTTPException(status_code=404, detail="版本不存在。")

    content = version_file.read_bytes()
    if target_file.name == "SKILL.md":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise HTTPException(status_code=422, detail="SKILL.md 版本必须是 UTF-8 文本。") from e
        valid, reason = dispatcher._validate_skill_frontmatter(skill_id, text)
        if not valid:
            raise HTTPException(status_code=422, detail=reason)

    if not req.approval_id:
        approval = record_approval_request(
            tool_call_id=f"rollback-{skill_id}-{int(time.time_ns())}",
            session_id="api",
            tool_name="rollback_skill",
            args={
                "skill_id": skill_id,
                "file_name": target_file.name,
                "version_id": version_file.name,
                "target_file": str(target_file),
                "version_file": str(version_file),
            },
            reason="用户请求回滚平台技能文件，必须人工审批并审计。",
            context={"asset_type": "platform", "protocol": "api", "trigger_source": "skills.rollback_api"},
        )
        return ResponseModel(
            status="pending_approval",
            message="技能回滚已进入审批队列，审批通过后请携带 approval_id 再次提交。",
            data={"approval": approval, "approval_id": approval["id"]},
        )

    approval = get_approval_request(req.approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在。")
    if approval.get("tool_name") != "rollback_skill":
        raise HTTPException(status_code=422, detail="审批请求类型不匹配。")
    if approval.get("status") != "approved":
        raise HTTPException(status_code=409, detail="技能回滚审批尚未批准。")
    if approval.get("execution"):
        raise HTTPException(status_code=409, detail="该技能回滚审批已经执行过。")
    approved_args = approval.get("args") or {}
    if (
        approved_args.get("skill_id") != skill_id
        or approved_args.get("file_name") != target_file.name
        or approved_args.get("version_id") != version_file.name
    ):
        raise HTTPException(status_code=409, detail="审批请求与本次回滚目标不匹配。")

    backup_path = dispatcher._backup_existing_skill_file(str(target_file))
    atomic_replace_bytes(target_file, content)
    dispatcher.refresh_skills(force=True)
    result = {
        "status": "SUCCESS",
        "skill_id": skill_id,
        "file_name": req.file_name,
        "file_path": str(target_file),
        "backup_path": backup_path,
        "version_id": req.version_id,
        "restored_version_path": str(version_file),
    }
    try:
        record_approval_execution(req.approval_id, json.dumps(result, ensure_ascii=False))
    except KeyError:
        pass
    return ResponseModel(
        status="success",
        message=f"技能文件 {req.file_name} 已回滚到版本 {req.version_id}",
        data=result,
    )


@router.post("/skills/migrate", response_model=ResponseModel)
async def migrate_skill(req: MigrateRequest):
    """将外部卡带拷贝到专属的 my_custom_skills 目录"""
    import shutil

    CUSTOM_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = resolve_custom_skill_dir(req.target_dir_name)
    source_path = Path(req.source_path).expanduser().resolve()
    if not source_path.is_dir():
        raise HTTPException(status_code=422, detail="source_path 必须是技能目录。")
    if not (source_path / "SKILL.md").is_file():
        raise HTTPException(status_code=422, detail="source_path 必须包含 SKILL.md。")

    try:
        if dest_path.exists():
            shutil.rmtree(dest_path)

        shutil.copytree(source_path, dest_path)

        # 拷贝完成后通知 Dispatcher 重新加载
        from core.dispatcher import dispatcher

        dispatcher.refresh_skills(force=True)

        return ResponseModel(
            status="success", message=f"卡带 {req.target_dir_name} 已成功导入专属库！"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/models", response_model=ResponseModel)
async def get_models(provider_id: str | None = None, refresh: bool = False):
    # Dynamic fetch of models
    from core.agent import get_available_models_for_provider

    models = await get_available_models_for_provider(provider_id=provider_id, refresh=refresh)
    if models:
        return ResponseModel(status="success", data={"models": models})
    raise HTTPException(status_code=502, detail="Cannot fetch models.")


@router.get("/config/llm", response_model=ResponseModel)
async def get_llm_config():
    """【新功能】获取当前大模型配置"""
    import os

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key = ""

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OPENAI_BASE_URL="):
                    base_url = line.strip().split("=", 1)[1]
                elif line.startswith("OPENAI_API_KEY="):
                    api_key = line.strip().split("=", 1)[1]

    return ResponseModel(
        status="success",
        data={
            "base_url": os.environ.get("OPENAI_BASE_URL", base_url),
            "api_key": "********" if os.environ.get("OPENAI_API_KEY", api_key) else "",
        },
    )



from typing import List

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


@router.get("/config/agent-runtime", response_model=ResponseModel)
async def get_agent_runtime_config_endpoint():
    from core.agent import get_agent_runtime_config

    return ResponseModel(status="success", data={"config": get_agent_runtime_config()})


@router.post("/config/agent-runtime", response_model=ResponseModel)
async def update_agent_runtime_config_endpoint(req: AgentRuntimeConfigRequest):
    from core.agent import update_agent_runtime_config

    try:
        config = update_agent_runtime_config(req.chat_max_steps, req.headless_max_steps)
        update_env_file_values(
            {
                "OPSCORE_AGENT_MAX_STEPS": str(config["chat_max_steps"]),
                "OPSCORE_HEADLESS_AGENT_MAX_STEPS": str(config["headless_max_steps"]),
            }
        )
    except Exception as e:
        logger.error("保存 Agent 执行保护配置失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存 Agent 执行保护配置失败: {e}")
    return ResponseModel(status="success", data={"config": config}, message="Agent 执行保护配置已保存")


@router.get("/config/embedding")
async def get_embedding_config_endpoint():
    from core.agent import get_embedding_config

    model, dim = get_embedding_config()
    return {"status": "success", "data": {"model": model, "dim": dim}}


@router.post("/config/embedding", response_model=ResponseModel)
async def update_embedding_config_endpoint(req: EmbeddingConfigRequest):
    from core.agent import update_embedding_config
    import os

    try:
        update_embedding_config(req.model, req.dim)
        logger.info(
            f"Embedding config updated via API: model={req.model}, dim={req.dim}"
        )

        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        keys_to_filter = ["EMBEDDING_MODEL=", "EMBEDDING_DIM="]
        env_lines = [
            line
            for line in env_lines
            if not any(line.startswith(k) for k in keys_to_filter)
        ]

        env_lines.append(f"EMBEDDING_MODEL={req.model}\n")
        env_lines.append(f"EMBEDDING_DIM={req.dim}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)

        return ResponseModel(
            status="success",
            message=f"Embedding 配置已更新: model={req.model}, dim={req.dim}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/config/notifications", response_model=ResponseModel)
async def get_notification_config():
    """【新功能】获取当前的告警通道配置"""
    return ResponseModel(status="success", data=build_notification_config())


@router.post("/config/notifications", response_model=ResponseModel)
async def update_notification_config(req: NotificationConfigRequest):
    """【新功能】前端动态配置企业微信/钉钉告警机器人 Webhook 及邮件"""
    env_values = build_notification_env_values(req.model_dump())
    os.environ.update(env_values)

    # Optional: Write to .env file for persistence
    try:
        update_env_file_values(env_values)
    except Exception as e:
        logger.error(f"Failed to save .env file: {e}")

    logger.info("Notification Webhooks updated.")
    return ResponseModel(status="success", message="告警通道配置已保存并生效")


class TestNotificationRequest(BaseModel):
    channel: str  # "wechat", "dingtalk", "email"


@router.post("/config/notifications/test", response_model=ResponseModel)
async def test_notification_channel(req: TestNotificationRequest):
    """【新功能】测试通知渠道"""
    try:
        message = send_notification_channel_test(req.channel)
        return ResponseModel(status="success", message=message)
    except NotificationTestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"测试发送失败: {str(e)}") from e


@router.put("/session/{session_id}/permission", response_model=ResponseModel)
async def update_session_permission(session_id: str, req: PermissionUpdateRequest):
    """【新功能】动态提权/降权：在不中断 SSH 的情况下，修改当前会话的 AI 修改权限"""
    try:
        set_session_permission(
            ssh_manager.active_sessions,
            session_id,
            req.allow_modifications,
        )
    except SessionRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    logger.info(
        f"Session {session_id} permissions changed to: {req.allow_modifications}"
    )

    return ResponseModel(status="success", message="权限已实时更新")


@router.put("/session/{session_id}/heartbeat", response_model=ResponseModel)
async def update_session_heartbeat(session_id: str, req: HeartbeatUpdateRequest):
    """【新功能】动态开启或关闭心跳巡检"""
    try:
        set_session_heartbeat(
            ssh_manager.active_sessions,
            session_id,
            req.heartbeat_enabled,
            req.master_interval,
        )
    except SessionRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if req.master_interval is not None:
        logger.info(
            f"Session {session_id} master_interval updated to: {req.master_interval}s"
        )

    logger.info(f"Session {session_id} heartbeat changed to: {req.heartbeat_enabled}")

    return ResponseModel(status="success", message="心跳巡检状态已更新")


@router.get("/sessions/poll_all", response_model=ResponseModel)
async def poll_all_sessions_messages():
    """【新功能】全局长轮询获取所有后台会话的待推送消息，极大地降低大规模纳管时的请求数量"""
    with ssh_manager._sessions_lock:
        updates = drain_all_pending_messages(ssh_manager.active_sessions)

    return ResponseModel(status="success", data={"updates": updates})


@router.get("/session/{session_id}/poll", response_model=ResponseModel)
async def poll_session_messages(session_id: str):
    """【新功能】前端长轮询获取后台心跳主动推送的消息"""
    try:
        with ssh_manager._sessions_lock:
            pending = drain_session_pending_messages(
                ssh_manager.active_sessions,
                session_id,
                missing_detail="Session disconnected",
            )
    except SessionRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if pending:
        return ResponseModel(
            status="success",
            data={"messages": pending},
        )

    return ResponseModel(status="success", data={"messages": []})


@router.get("/session/{session_id}/history", response_model=ResponseModel)
async def get_session_history(session_id: str):
    """【新功能】获取会话的历史消息记录，用于前端恢复"""
    from core.memory import memory_db

    try:
        chat_history = get_user_visible_session_history(memory_db, session_id)
        return ResponseModel(status="success", data={"messages": chat_history})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/session/{session_id}/history", response_model=ResponseModel)
async def delete_session_history(session_id: str):
    """【新功能】清空会话的聊天记录"""
    from core.memory import memory_db

    try:
        clear_session_history_messages(memory_db, session_id)
        return ResponseModel(status="success", message="会话记录已清空")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def update_session_history_message(
    session_id: str,
    message_id: int,
    req: SessionMessageUpdateRequest,
):
    """修改单条用户可见会话消息。"""
    from core.memory import memory_db

    try:
        message = update_session_message_content(
            memory_db,
            session_id,
            message_id,
            req.content,
        )
        return ResponseModel(status="success", data={"message": message}, message="消息已更新")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def delete_session_history_message(session_id: str, message_id: int):
    """删除单条用户可见会话消息。"""
    from core.memory import memory_db

    try:
        delete_session_message(memory_db, session_id, message_id)
        return ResponseModel(status="success", message="消息已删除")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/session/{session_id}/skills", response_model=ResponseModel)
async def update_session_skills(session_id: str, req: SkillsUpdateRequest):
    """【新功能】动态修改挂载技能包：在不中断会话的情况下，挂载或卸载 AI 技能"""
    try:
        set_session_skills(ssh_manager.active_sessions, session_id, req.active_skills)
    except SessionRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    logger.info(f"Session {session_id} active skills changed to: {req.active_skills}")

    return ResponseModel(status="success", message="挂载技能已实时更新")


@router.put("/session/{session_id}/group", response_model=ResponseModel)
async def update_session_group(session_id: str, req: SessionGroupUpdateRequest):
    """更新活跃会话的主分组；底层复用现有 tags[0]，保持旧会话结构兼容。"""
    try:
        info, group_name = set_session_group(
            ssh_manager.active_sessions,
            session_id,
            req.group_name,
        )
    except SessionRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    logger.info("Session %s group changed to: %s", session_id, group_name)

    return ResponseModel(
        status="success",
        message="会话分组已更新",
        data={"session_id": session_id, "tags": info["tags"], "group_name": group_name},
    )


@router.get("/sessions/active", response_model=ResponseModel)
async def get_active_sessions():
    """【新功能】前端刷新页面时同步当前后端的活跃会话"""
    from core.chat_runs import is_chat_running
    from core.memory import memory_db

    sessions_data = build_active_sessions_response(
        ssh_manager.active_sessions,
        is_session_streaming=is_chat_running,
        sensitive_keys=memory_db.sensitive_keys,
    )
    return ResponseModel(status="success", data={"sessions": sessions_data})


def build_session_tool_context(info: dict) -> dict:
    identity = resolve_asset_identity(
        info.get("asset_type"),
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    return {
        "session_id": info.get("session_id"),
        "target_scope": info.get("target_scope", "asset"),
        "scope_value": info.get("scope_value"),
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "host": info.get("host"),
        "port": info.get("port"),
        "remark": info.get("remark"),
        "extra_args": identity["extra_args"],
    }


@router.get("/tools/catalog", response_model=ResponseModel)
async def get_tool_catalog():
    """返回平台内置工具目录。仅包含工具元数据，不包含任何资产凭据。"""
    return ResponseModel(status="success", data=tool_registry.catalog())


@router.get("/session/{session_id}/tools", response_model=ResponseModel)
async def get_session_tools(session_id: str):
    """返回指定会话当前会暴露给模型的工具集。"""
    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    info = dict(ssh_manager.active_sessions[session_id]["info"])
    info["session_id"] = session_id
    context = build_session_tool_context(info)
    catalog = tool_registry.catalog(context)
    active_tools = [
        tool["name"]
        for toolset in catalog["toolsets"]
        for tool in toolset["tools"]
        if tool.get("enabled")
    ]
    return ResponseModel(
        status="success",
        data={
            **catalog,
            "active_tools": active_tools,
            "context": {
                "target_scope": context["target_scope"],
                "asset_type": context["asset_type"],
                "protocol": context["protocol"],
                "host": context["host"],
                "port": context["port"],
            },
        },
    )


@router.get("/session/{session_id}/commands", response_model=ResponseModel)
async def get_session_commands(session_id: str):
    """返回当前会话可用 Slash Commands；由后端根据资产协议生成 prompt。"""
    from core.slash_commands import render_builtin_templates, render_slash_commands
    from core.memory import memory_db

    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    tools_response = await get_session_tools(session_id)
    custom_commands = await asyncio.to_thread(memory_db.list_slash_commands)
    commands = render_slash_commands(
        tools_response.data["context"],
        tools_response.data.get("active_tools") or [],
        custom_commands,
    )
    builtin_commands = render_builtin_templates(
        tools_response.data["context"],
        tools_response.data.get("active_tools") or [],
        custom_commands,
    )
    return ResponseModel(
        status="success",
        data={
            "commands": commands,
            "builtin_commands": builtin_commands,
            "custom_commands": custom_commands,
            "context": tools_response.data["context"],
        },
    )


@router.get("/commands/custom", response_model=ResponseModel)
async def list_custom_slash_commands():
    """列出用户自定义快捷命令。"""
    from core.memory import memory_db

    commands = await asyncio.to_thread(memory_db.list_slash_commands)
    return ResponseModel(status="success", data={"commands": commands})


@router.post("/commands/custom", response_model=ResponseModel)
async def create_custom_slash_command(req: SlashCommandPayload):
    """创建用户自定义快捷命令。"""
    from core.memory import memory_db

    command = await asyncio.to_thread(memory_db.save_slash_command, req.model_dump())
    return ResponseModel(status="success", message="快捷命令已保存", data={"command": command})


@router.put("/commands/custom/{command_id}", response_model=ResponseModel)
async def update_custom_slash_command(command_id: str, req: SlashCommandPayload):
    """更新用户自定义快捷命令。"""
    from core.memory import memory_db

    payload = req.model_dump()
    payload["id"] = command_id
    command = await asyncio.to_thread(memory_db.save_slash_command, payload)
    return ResponseModel(status="success", message="快捷命令已更新", data={"command": command})


@router.delete("/commands/custom/{command_id}", response_model=ResponseModel)
async def delete_custom_slash_command(command_id: str):
    """删除用户自定义快捷命令。"""
    from core.memory import memory_db

    deleted = await asyncio.to_thread(memory_db.delete_slash_command, command_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="快捷命令不存在")
    return ResponseModel(status="success", message="快捷命令已删除")


@router.get("/inspection-templates", response_model=ResponseModel)
async def list_inspection_templates():
    """列出内置与自定义巡检模板。"""
    from core.inspection_templates import list_templates

    return ResponseModel(status="success", data={"templates": list_templates()})


@router.post("/inspection-templates", response_model=ResponseModel)
async def create_inspection_template(req: InspectionTemplatePayload):
    """创建巡检模板；模板必须通过只读安全校验。"""
    from core.inspection_templates import save_template

    try:
        template = save_template(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ResponseModel(status="success", message="巡检模板已保存", data={"template": template})


@router.put("/inspection-templates/{template_id}", response_model=ResponseModel)
async def update_inspection_template(template_id: str, req: InspectionTemplatePayload):
    """更新巡检模板；路径 ID 优先，避免请求体误改主键。"""
    from core.inspection_templates import save_template

    payload = req.model_dump()
    payload["id"] = template_id
    try:
        template = save_template(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ResponseModel(status="success", message="巡检模板已更新", data={"template": template})


@router.delete("/inspection-templates/{template_id}", response_model=ResponseModel)
async def delete_inspection_template(template_id: str):
    """删除巡检模板。"""
    from core.inspection_templates import delete_template

    if not delete_template(template_id):
        raise HTTPException(status_code=404, detail="巡检模板不存在")
    return ResponseModel(status="success", message="巡检模板已删除")


@router.post("/session/{session_id}/inspect", response_model=ResponseModel)
async def inspect_active_session(session_id: str):
    """对已建立的会话执行只读巡检。"""
    from core.session_inspector import inspect_session

    report = await inspect_session(session_id)
    return ResponseModel(
        status="success" if report.get("status") in {"success", "warning"} else report.get("status", "error"),
        message=report.get("summary") or report.get("message", ""),
        data={"inspection": report},
    )


@router.get("/session/{session_id}/profile", response_model=ResponseModel)
async def get_active_session_profile(session_id: str):
    """读取当前会话沉淀的资产画像。"""
    from core.session_profile import get_session_profile

    profile = await asyncio.to_thread(get_session_profile, session_id)
    return ResponseModel(status="success", data={"profile": profile})


@router.post("/session/{session_id}/profile/generate", response_model=ResponseModel)
async def generate_active_session_profile(session_id: str, req: SessionProfileGenerateRequest):
    """基于会话历史和只读巡检生成资产画像，并写入独立画像记忆。"""
    from core.session_profile import generate_session_profile

    try:
        profile = await generate_session_profile(
            session_id,
            model_name=req.model_name,
            include_inspection=req.include_inspection,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return ResponseModel(status="success", message="资产画像已生成", data={"profile": profile})


def _build_session_history_markdown(session_id: str) -> str:
    from core.memory import memory_db

    return build_session_history_markdown_content(
        memory_db,
        ssh_manager.active_sessions,
        session_id,
    )


async def _build_session_webhook_markdown(
    session_id: str,
    payload_type: str,
    model_name: str | None,
) -> tuple[str, dict | None]:
    from core.session_profile import generate_session_profile, get_session_profile, profile_to_markdown

    normalized = str(payload_type or "profile").lower()
    if normalized == "markdown":
        return await asyncio.to_thread(_build_session_history_markdown, session_id), None

    profile = await asyncio.to_thread(get_session_profile, session_id)
    if not profile:
        profile = await generate_session_profile(session_id, model_name=model_name, include_inspection=False)
    profile_md = profile_to_markdown(profile)
    if normalized == "profile":
        return profile_md, profile

    history_md = await asyncio.to_thread(_build_session_history_markdown, session_id)
    summary = history_md[:1800] if history_md else "当前会话暂无可发送的聊天摘要。"
    return f"{profile_md}\n\n## 会话摘要\n\n{summary}", profile


def _validate_webhook_url(url: str, allow_private_targets: bool = False) -> tuple[str, dict]:
    try:
        return validate_webhook_url(url, allow_private_targets)
    except SessionWebhookError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _build_session_webhook_payload(
    session_id: str,
    payload_type: str,
    channel: str,
    title: str,
    markdown: str,
    profile: dict | None,
) -> dict:
    return build_session_webhook_payload(session_id, payload_type, channel, title, markdown, profile)


def _webhook_payload_preview(payload: dict) -> dict:
    return webhook_payload_preview(payload)


def _post_webhook(url: str, payload: dict) -> tuple[int, str]:
    return post_webhook(url, payload)


@router.post("/session/{session_id}/webhook/send", response_model=ResponseModel)
async def send_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """将会话画像、摘要或完整 Markdown 发送到指定 Webhook。"""
    webhook_url, target = _validate_webhook_url(req.webhook_url, req.allow_private_targets)
    payload_type = str(req.payload_type or "profile").lower()
    if payload_type not in {"profile", "summary", "markdown"}:
        raise HTTPException(status_code=422, detail="payload_type 仅支持 profile、summary、markdown。")
    channel = str(req.channel or "generic").lower()
    if channel not in {"generic", "wechat", "dingtalk"}:
        raise HTTPException(status_code=422, detail="channel 仅支持 generic、wechat、dingtalk。")

    markdown, profile = await _build_session_webhook_markdown(
        session_id,
        payload_type,
        req.model_name,
    )
    if not markdown.strip():
        raise HTTPException(status_code=404, detail="当前会话没有可发送内容。")

    title = req.title or f"OpsCore 会话报告 {session_id}"
    payload = _build_session_webhook_payload(session_id, payload_type, channel, title, markdown, profile)

    from core.memory import memory_db

    try:
        status_code, response_body = await asyncio.to_thread(_post_webhook, webhook_url, payload)
        record = {
            "session_id": session_id,
            "webhook_host": target["host"],
            "channel": channel,
            "payload_type": payload_type,
            "title": title,
            "status": "success" if status_code < 400 else "error",
            "http_status": status_code,
            "response_preview": response_body[:300],
            "error": "" if status_code < 400 else f"HTTP {status_code}",
        }
        await asyncio.to_thread(memory_db.append_webhook_delivery, record)
    except Exception as e:
        record = {
            "session_id": session_id,
            "webhook_host": target["host"],
            "channel": channel,
            "payload_type": payload_type,
            "title": title,
            "status": "error",
            "http_status": None,
            "response_preview": "",
            "error": str(e)[:500],
        }
        await asyncio.to_thread(memory_db.append_webhook_delivery, record)
        raise

    if status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Webhook 返回 HTTP {status_code}: {response_body[:300]}")
    return ResponseModel(
        status="success",
        message="Webhook 已发送",
        data={"http_status": status_code, "response_preview": response_body[:300], "target": target},
    )


@router.post("/session/{session_id}/webhook/preview", response_model=ResponseModel)
async def preview_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """发送前预览会话 Webhook 目标和载荷，不实际发出请求。"""
    _, target = _validate_webhook_url(req.webhook_url, req.allow_private_targets)
    payload_type = str(req.payload_type or "profile").lower()
    if payload_type not in {"profile", "summary", "markdown"}:
        raise HTTPException(status_code=422, detail="payload_type 仅支持 profile、summary、markdown。")
    channel = str(req.channel or "generic").lower()
    if channel not in {"generic", "wechat", "dingtalk"}:
        raise HTTPException(status_code=422, detail="channel 仅支持 generic、wechat、dingtalk。")
    markdown, profile = await _build_session_webhook_markdown(session_id, payload_type, req.model_name)
    if not markdown.strip():
        raise HTTPException(status_code=404, detail="当前会话没有可发送内容。")
    title = req.title or f"OpsCore 会话报告 {session_id}"
    payload = _build_session_webhook_payload(session_id, payload_type, channel, title, markdown, profile)
    return ResponseModel(
        status="success",
        data={
            "target": target,
            "payload_type": payload_type,
            "channel": channel,
            "title": title,
            "payload": _webhook_payload_preview(payload),
        },
    )


@router.get("/session/{session_id}/webhook/history", response_model=ResponseModel)
async def list_session_webhook_history(session_id: str, limit: int = 10):
    """查看当前会话最近 Webhook 发送历史。"""
    from core.memory import memory_db

    deliveries = await asyncio.to_thread(memory_db.list_webhook_deliveries, session_id, limit)
    return ResponseModel(status="success", data={"deliveries": deliveries})


@router.delete("/disconnect/{session_id}", response_model=ResponseModel)
async def close_ssh_connection(session_id: str):
    """大模型或者前端关闭会话释放资源"""
    success = await asyncio.to_thread(ssh_manager.disconnect, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return ResponseModel(status="success", message="Connection closed safely")


@router.get("/assets/saved", response_model=ResponseModel)
async def get_saved_assets():
    """【新功能】获取 SQLite 中持久化的所有资产信息（通讯录）"""
    from core.memory import memory_db

    assets = await asyncio.to_thread(memory_db.get_all_assets)
    return ResponseModel(status="success", data={"assets": mask_asset_responses(assets, memory_db.sensitive_keys)})


@router.post("/assets", response_model=ResponseModel)
async def create_asset(req: AssetPayload):
    """创建或按 host+资产类型+协议更新资产；密码和敏感 extra_args 会加密保存。"""
    from core.memory import memory_db

    await asyncio.to_thread(
        memory_db.save_asset,
        req.remark or "",
        req.host,
        req.port,
        req.username,
        req.password,
        req.asset_type,
        req.agent_profile,
        req.extra_args,
        req.skills,
        req.tags,
        req.protocol,
    )
    return ResponseModel(status="success", message="资产已保存")


def _asset_types_response() -> ResponseModel:
    return ResponseModel(status="success", data=build_asset_types_response(get_asset_catalog()))


@router.get("/assets/types", response_model=ResponseModel)
async def get_asset_types():
    """返回后端认可的资产类型与默认登录协议目录。"""
    return _asset_types_response()


@router.get("/oracle/client-config", response_model=ResponseModel)
async def get_oracle_client_config():
    """返回本机 Oracle Instant Client 自动探测结果，供前端填充 Thick Mode 配置。"""
    from connections.db_manager import discover_oracle_client_lib_dir

    return ResponseModel(status="success", data=discover_oracle_client_lib_dir())


@router.get("/database/driver-capabilities", response_model=ResponseModel)
async def get_database_driver_capabilities_api():
    """返回数据库连接器、Python 包和外部客户端安装状态。"""
    from connections.db_manager import get_database_driver_capabilities

    return ResponseModel(status="success", data=get_database_driver_capabilities())


@router.get("/assets/{asset_id}", response_model=ResponseModel)
async def get_asset(asset_id: int):
    """查询单个资产详情；响应会脱敏密码和敏感 extra_args。"""
    from core.memory import memory_db

    asset = await asyncio.to_thread(memory_db.get_asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return ResponseModel(status="success", data={"asset": mask_asset_response(asset, memory_db.sensitive_keys)})


@router.put("/assets/{asset_id}", response_model=ResponseModel)
async def update_asset(asset_id: int, req: AssetPayload):
    """按资产 ID 修改资产；传入 ******** 会保留原密码/密钥。"""
    from core.memory import memory_db

    asset = await asyncio.to_thread(memory_db.update_asset, asset_id, req.model_dump())
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return ResponseModel(
        status="success",
        message="资产已更新",
        data={"asset": mask_asset_response(asset, memory_db.sensitive_keys)},
    )


@router.get("/assets/normalize/preview", response_model=ResponseModel)
async def preview_asset_normalization():
    """预览资产协议、host/port 与重复数据清理计划。"""
    from core.asset_cleanup import build_asset_cleanup_plan

    plan = await asyncio.to_thread(build_asset_cleanup_plan)
    return ResponseModel(status="success", data=plan)


@router.post("/assets/normalize/apply", response_model=ResponseModel)
async def apply_asset_normalization():
    """执行资产规范化清理；执行前会生成本地备份文件。"""
    from core.asset_cleanup import apply_asset_cleanup

    report = await asyncio.to_thread(apply_asset_cleanup)
    return ResponseModel(status="success", message="资产规范化清理完成", data=report)


@router.delete("/assets/{asset_id}", response_model=ResponseModel)
async def delete_saved_asset(asset_id: int):
    """【新功能】删除持久化的资产"""
    from core.memory import memory_db

    await asyncio.to_thread(memory_db.delete_asset, asset_id)
    return ResponseModel(status="success", message="资产已成功移除金库。")


@router.get("/dashboard/overview", response_model=ResponseModel)
async def get_dashboard_overview():
    """大屏总览接口：资产、在线会话、协议、分类和基础风险计数。"""
    from core.memory import memory_db
    from core.alert_events import alert_summary
    from core.cron_manager import CronManager
    from core.inspection_results import run_summary

    assets = await asyncio.to_thread(memory_db.get_all_assets)
    active = list(ssh_manager.active_sessions.values())
    return ResponseModel(
        status="success",
        data=build_dashboard_overview(
            assets,
            active,
            CronManager.get_all_jobs(),
            alert_summary(),
            run_summary(),
        ),
    )


@router.get("/dashboard/toolsets", response_model=ResponseModel)
async def get_dashboard_toolsets():
    """大屏/配置页工具集接口：展示平台工具覆盖度。"""
    catalog = tool_registry.catalog()
    return ResponseModel(status="success", data=catalog)


@router.get("/dashboard/alerts/trend", response_model=ResponseModel)
async def get_dashboard_alert_trend():
    """大屏告警趋势接口，按日期聚合告警数量和严重级别。"""
    from core.alert_events import list_alert_events

    return ResponseModel(status="success", data={"points": build_alert_trend(list_alert_events(limit=5000))})


@router.get("/dashboard/risk-ranking", response_model=ResponseModel)
async def get_dashboard_risk_ranking():
    """大屏风险排行接口，当前按告警数量和严重度聚合主机风险。"""
    from core.alert_events import list_alert_events

    return ResponseModel(status="success", data={"ranking": build_risk_ranking(list_alert_events(limit=5000))})


@router.get("/dashboard/inspection-runs/trend", response_model=ResponseModel)
async def get_dashboard_inspection_run_trend():
    from core.inspection_results import run_trend

    return ResponseModel(status="success", data={"points": run_trend()})


@router.get("/verification/protocols", response_model=ResponseModel)
async def get_protocol_verification_overview():
    """返回全量资产协议验证矩阵概览，不包含任何敏感凭据。"""
    from core.memory import memory_db
    from core.protocol_verification import build_overview

    assets = await asyncio.to_thread(memory_db.get_all_assets)
    return ResponseModel(status="success", data=build_overview(assets))


@router.get("/assets/{asset_id}/verification", response_model=ResponseModel)
async def get_asset_verification_matrix(asset_id: int):
    """返回单资产协议验证矩阵，不包含任何敏感凭据。"""
    from core.memory import memory_db
    from core.protocol_verification import build_asset_matrix

    asset = await asyncio.to_thread(memory_db.get_asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return ResponseModel(status="success", data={"matrix": build_asset_matrix(asset)})


@router.post("/assets/{asset_id}/verify", response_model=ResponseModel)
async def verify_asset(asset_id: int):
    """执行单资产只读端到端验证，并持久化验证历史。"""
    from core.memory import memory_db
    from core.protocol_verification import run_asset_verification

    asset = await asyncio.to_thread(memory_db.get_asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    run = await run_asset_verification(asset)
    return ResponseModel(status="success", data={"run": run})


@router.get("/assets/{asset_id}/verification/runs", response_model=ResponseModel)
async def list_asset_verification_runs(asset_id: int, limit: int = 20):
    """查询单资产验证历史。"""
    from core.protocol_verification import list_verification_runs

    return ResponseModel(status="success", data={"runs": list_verification_runs(asset_id=asset_id, limit=limit)})


@router.get("/alerts", response_model=ResponseModel)
async def list_alert_events(status: str | None = None, severity: str | None = None, host: str | None = None, limit: int = 200):
    """查询告警事件。"""
    from core.alert_events import list_alert_events as list_events

    return ResponseModel(
        status="success",
        data={"alerts": list_events(status=status, severity=severity, host=host, limit=limit)},
    )


@router.get("/alerts/{alert_id}", response_model=ResponseModel)
async def get_alert_event(alert_id: str):
    """查询单个告警事件。"""
    from core.alert_events import get_alert_event as get_event

    alert = get_event(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警事件不存在")
    return ResponseModel(status="success", data={"alert": alert})


@router.patch("/alerts/{alert_id}", response_model=ResponseModel)
async def update_alert_event(alert_id: str, req: AlertEventUpdateRequest):
    """更新告警状态、处理人或备注。"""
    from core.alert_events import update_alert_event as update_event

    try:
        alert = update_event(
            alert_id,
            status=req.status,
            assignee=req.assignee,
            note=req.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not alert:
        raise HTTPException(status_code=404, detail="告警事件不存在")
    return ResponseModel(status="success", data={"alert": alert})


# ----------------- OpenClaw / ManageEngine Webhook 闭环设计 -----------------
from fastapi import Request

from fastapi import UploadFile, File


@router.post("/knowledge/upload", response_model=ResponseModel)
async def upload_knowledge_document(file: UploadFile = File(...)):
    """【新功能】上传运维文档并注入 LanceDB 知识库"""
    import os
    import re
    import uuid

    original_name = os.path.basename(file.filename or "")
    stem, ext = os.path.splitext(original_name)
    allowed_exts = {".txt", ".md", ".pdf", ".doc", ".docx", ".log"}
    if ext.lower() not in allowed_exts:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的知识库文件类型: {ext or 'unknown'}",
        )

    from core.rag import kb_manager
    from core.llm_factory import get_embedding_client_and_model

    client, embedding_model = get_embedding_client_and_model()

    safe_stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", stem).strip("._-") or "document"
    safe_filename = f"{safe_stem}-{uuid.uuid4().hex[:8]}{ext.lower()}"
    file_path = os.path.join(kb_manager.kb_dir, safe_filename)
    max_bytes = 50 * 1024 * 1024
    written = 0
    with open(file_path, "wb") as buffer:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                buffer.close()
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                raise HTTPException(status_code=413, detail="知识库文件超过 50MB 限制")
            buffer.write(chunk)

    try:
        res = await kb_manager.ingest_document(file_path, client, embedding_model)
        if res["status"] == "success":
            return ResponseModel(status="success", message=res["message"])
        else:
            raise HTTPException(status_code=422, detail=res["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/knowledge/list", response_model=ResponseModel)
async def list_knowledge_documents():
    """【新功能】列出已注入知识库的文档列表"""
    from core.rag import kb_manager

    try:
        files = await kb_manager.list_documents()
        return ResponseModel(status="success", data={"files": files})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/knowledge/{filename}", response_model=ResponseModel)
async def delete_knowledge_document(filename: str):
    """【新功能】从知识库中删除某个文档"""
    from core.rag import kb_manager

    try:
        res = await kb_manager.delete_document(filename)
        if res["status"] == "success":
            return ResponseModel(status="success", message=res["message"])
        else:
            raise HTTPException(status_code=404, detail=res["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/webhook/alert", response_model=ResponseModel)
async def receive_webhook_alert(request: Request):
    """【AIOps 高级特性】接收外部告警 (Prometheus / ManageEngine) 并推入相关 AI 会话"""
    from core.alert_events import create_alert_event

    try:
        payload = await request.json()
    except (ValueError, TypeError):
        payload = {}

    alert_event = create_alert_event(payload)

    # 兼容卓豪 (ManageEngine) 和 Prometheus 等常见告警系统的数据结构
    # 提取主机/节点信息
    host = alert_event["host"]

    # 提取告警标题
    alert_name = alert_event["alert_name"]

    logger.info(
        "Webhook alert received: host=%s alert=%s severity=%s keys=%s",
        host,
        alert_name,
        payload.get("severity") or payload.get("priority") or payload.get("status") or "",
        sorted(list(payload.keys()))[:20],
    )

    # 提取严重程度
    severity = alert_event["severity"]

    # 提取详情
    description = alert_event["description"]

    logger.info(
        f"Parsed Alert -> Host: {host}, Name: {alert_name}, Severity: {severity}"
    )

    # 查找所有当前连接到该故障主机的活跃 SSH 会话（或者如果系统有总管身份，也会收到）
    affected_sessions = []
    for sid, sdata in list(ssh_manager.active_sessions.items()):
        if (
            sdata["info"]["host"] == host
            or host == "all"
            or sdata["info"]["host"] == "localhost"
        ):  # localhost 监控总管也会兜底收到
            affected_sessions.append(sid)

    if not affected_sessions:
        logger.warning(
            f"Alert received but no active AI session is connected to {host} or localhost."
        )
        return ResponseModel(
            status="success",
            message="告警已接收，但目前无人值守，已记录日志。",
            data={"alert": alert_event, "injected_count": 0},
        )

    # 从内存中提取 Agent 的对话历史，强行塞入一条【系统通知】
    from core.memory import memory_db
    from core.dispatcher import dispatcher
    from core.heartbeat import run_single_heartbeat
    import asyncio

    injection_msg = f"🔔 【监控告警接入】外部系统触发了级别为 [{str(severity).upper()}] 的告警。\n**告警名称**：{alert_name}\n**故障节点**：{host}\n**详细信息**：\n{description}\n\n作为监控专家，请主动分析此告警。如果你是负责整个环境的指挥官（例如你的连接是 localhost），请使用 `list_active_sessions` 查找合适的子节点并使用 `dispatch_sub_agents` 派发调查任务；如果你是具体服务器的节点 Agent，请立刻调用技能/工具去探查根因！"

    injected_count = 0
    for sid in affected_sessions:
        info = ssh_manager.active_sessions[sid].get("info", {})

        # 使用真实的 asyncio Lock 解决高并发告警风暴下的竞态条件 (Race Condition)
        lock = webhook_locks.setdefault(sid, asyncio.Lock())
        async with lock:
            if info.get("heartbeat_in_progress"):
                # 如果当前该 session 正在后台自主巡检，则退化为仅追加日志
                memory_db.append_message(sid, {"role": "user", "content": injection_msg})
                logger.info(f"Session {sid} is busy, appended alert to context only.")
            else:
                info["heartbeat_in_progress"] = True
                logger.info(
                    f"Actively triggering background AI task for session {sid} due to alert."
                )
                asyncio.create_task(
                    run_single_heartbeat(
                        sid, info, memory_db, dispatcher, trigger_msg=injection_msg
                    )
                )

        injected_count += 1

    return ResponseModel(
        status="success",
        message=f"告警已成功推送到 {injected_count} 个值班中的 AI 大脑中，并已唤醒 AI 进行排查！",
        data={"alert": alert_event, "injected_count": injected_count},
    )


# ----------------- OpenClaw 自动化巡检 (Cron Jobs) -----------------
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


@router.post("/cron/add", response_model=ResponseModel)
async def add_cron_job(req: CronAddRequest):
    """【新功能】添加大模型定时巡检任务 (类似 openclaw cron add)"""
    from core.cron_manager import CronManager

    try:
        job_id = CronManager.add_inspection_job(
            cron_expr=req.cron_expr,
            host=req.host,
            username=req.username,
            agent_profile=req.agent_profile,
            message=req.message,
            password=req.password,
            private_key_path=req.private_key_path,
            asset_id=req.asset_id,
            target_scope=req.target_scope,
            scope_value=req.scope_value,
            template_id=req.template_id,
            notification_channel=req.notification_channel,
            retry_count=req.retry_count,
            active_skills=req.active_skills,
        )
        return ResponseModel(
            status="success",
            message=f"已成功添加定时巡检计划: {job_id}",
            data={"job_id": job_id, "job": CronManager.get_job(job_id)},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cron/list", response_model=ResponseModel)
async def list_cron_jobs():
    """【新功能】查看所有的定时巡检计划"""
    from core.cron_manager import CronManager

    jobs = CronManager.get_all_jobs()
    return ResponseModel(status="success", data={"jobs": jobs})


@router.delete("/cron/{job_id}", response_model=ResponseModel)
async def delete_cron_job(job_id: str):
    """【新功能】删除某个定时巡检计划"""
    from core.cron_manager import CronManager

    try:
        CronManager.remove_job(job_id)
        return ResponseModel(status="success", message=f"巡检计划 {job_id} 已取消。")
    except Exception:
        raise HTTPException(status_code=404, detail="未找到该计划。")


@router.put("/cron/{job_id}", response_model=ResponseModel)
async def update_cron_job(job_id: str, req: CronAddRequest):
    from core.cron_manager import CronManager

    try:
        job = CronManager.update_job(
            job_id,
            cron_expr=req.cron_expr,
            host=req.host,
            username=req.username,
            agent_profile=req.agent_profile,
            message=req.message,
            password=req.password,
            private_key_path=req.private_key_path,
            asset_id=req.asset_id,
            target_scope=req.target_scope,
            scope_value=req.scope_value,
            template_id=req.template_id,
            notification_channel=req.notification_channel,
            retry_count=req.retry_count,
            active_skills=req.active_skills,
        )
        return ResponseModel(status="success", message="巡检计划已更新", data={"job": job})
    except KeyError:
        raise HTTPException(status_code=404, detail="未找到该计划。")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cron/{job_id}/pause", response_model=ResponseModel)
async def pause_cron_job(job_id: str):
    from core.cron_manager import CronManager

    try:
        return ResponseModel(status="success", message="巡检计划已暂停", data={"job": CronManager.pause_job(job_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="未找到该计划。")


@router.post("/cron/{job_id}/resume", response_model=ResponseModel)
async def resume_cron_job(job_id: str):
    from core.cron_manager import CronManager

    try:
        return ResponseModel(status="success", message="巡检计划已恢复", data={"job": CronManager.resume_job(job_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="未找到该计划。")


@router.post("/cron/{job_id}/run", response_model=ResponseModel)
async def run_cron_job_now(job_id: str):
    from core.cron_manager import CronManager

    try:
        result = await CronManager.run_job_now(job_id)
        return ResponseModel(status="success", message="巡检计划已手动触发", data={"result": result})
    except KeyError:
        raise HTTPException(status_code=404, detail="未找到该计划。")


@router.get("/cron/{job_id}/runs", response_model=ResponseModel)
async def list_cron_job_runs(job_id: str, limit: int = 50, asset_id: int | None = None):
    from core.inspection_results import list_runs

    return ResponseModel(status="success", data={"runs": list_runs(job_id=job_id, limit=limit, asset_id=asset_id)})


@router.get("/inspection-runs", response_model=ResponseModel)
async def list_inspection_runs(job_id: str | None = None, asset_id: int | None = None, limit: int = 50):
    from core.inspection_results import list_runs

    return ResponseModel(status="success", data={"runs": list_runs(job_id=job_id, asset_id=asset_id, limit=limit)})


@router.get("/cron/runs/summary", response_model=ResponseModel)
async def get_cron_run_summary():
    from core.inspection_results import run_summary

    return ResponseModel(status="success", data={"summary": run_summary()})


@router.get("/cron/runs/{run_id}", response_model=ResponseModel)
async def get_cron_job_run(run_id: str):
    from core.inspection_results import get_run

    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="巡检运行记录不存在")
    return ResponseModel(status="success", data={"run": run})


@router.get("/inspection-runs/{run_id}/report", response_model=ResponseModel)
async def get_inspection_run_report(run_id: str):
    from core.inspection_results import build_report

    report = build_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="巡检报告不存在")
    return ResponseModel(status="success", data={"report": report})


@router.get("/inspection-runs/{run_id}/export", response_model=ResponseModel)
async def export_inspection_run_report(run_id: str, format: str = "markdown"):
    from core.inspection_results import build_report, export_report_markdown

    normalized = str(format or "markdown").lower()
    if normalized in {"md", "markdown"}:
        content = export_report_markdown(run_id)
        content_type = "text/markdown"
    elif normalized == "json":
        report = build_report(run_id)
        content = json.dumps(report, ensure_ascii=False, indent=2) if report else None
        content_type = "application/json"
    else:
        raise HTTPException(status_code=422, detail="format 仅支持 markdown 或 json")
    if content is None:
        raise HTTPException(status_code=404, detail="巡检报告不存在")
    return ResponseModel(status="success", data={"format": normalized, "content_type": content_type, "content": content})


# ----------------- 系统状态与高级功能 -----------------


@router.get("/hydrate/status", response_model=ResponseModel)
async def get_hydrate_status():
    """【新功能】获取启动时资产重连的进度，前端可轮询此接口展示启动状态"""
    from main import hydrate_status

    return ResponseModel(status="success", data=hydrate_status)


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


@router.post("/assets/batch_import", response_model=ResponseModel)
async def batch_import_assets(items: list[BatchAssetImportItem]):
    """【#25 新功能】批量导入资产到金库（通讯录），支持 JSON 数组格式"""
    from core.memory import memory_db

    if not items:
        raise HTTPException(status_code=422, detail="批量导入资产列表不能为空。")
    try:
        await asyncio.to_thread(
            memory_db.save_assets_batch, [item.model_dump() for item in items]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量导入资产失败: {e}") from e

    return ResponseModel(status="success", message=f"成功导入 {len(items)}/{len(items)} 条资产。")


@router.get("/session/{session_id}/export", response_model=ResponseModel)
async def export_session_history(session_id: str):
    """【#22 新功能】服务端导出会话历史为 Markdown 格式"""
    from core.memory import memory_db

    try:
        markdown = build_session_history_markdown_content(
            memory_db,
            ssh_manager.active_sessions,
            session_id,
        )
        if not markdown:
            raise HTTPException(status_code=404, detail="该会话没有可导出的历史记录。")

        return ResponseModel(status="success", data={"markdown": markdown})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/config/providers", response_model=ResponseModel)
async def get_providers_endpoint():
    from core.llm_factory import get_all_providers, mask_provider_secrets
    providers = mask_provider_secrets(get_all_providers())
    return ResponseModel(status="success", data={"providers": providers})

@router.post("/config/providers", response_model=ResponseModel)
async def update_providers_endpoint(req: List[ProviderConfig]):
    from core.llm_factory import get_all_providers, merge_provider_secrets, save_providers

    try:
        providers_dict = merge_provider_secrets(
            [p.model_dump() for p in req],
            get_all_providers(),
        )
        save_providers(providers_dict)
    except Exception as e:
        logger.error("保存模型供应商配置失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存供应商配置失败: {e}")
    return ResponseModel(status="success", message="供应商配置已保存")


class SafetyPolicyUpdateRequest(BaseModel):
    policy: dict


SAFETY_POLICY_TEST_TOOLS = {
    "linux_execute_command",
    "container_execute_command",
    "middleware_execute_command",
    "storage_execute_command",
    "network_cli_execute_command",
    "execute_on_scope",
    "winrm_execute_command",
    "db_execute_query",
    "redis_execute_command",
    "memcached_execute_command",
    "mongodb_find",
    "http_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "k8s_api_request",
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "service_probe_request",
    "snmp_get",
    "local_execute_script",
    "evolve_skill",
}


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
        if self.tool_name == "db_execute_query":
            return {"sql": self.sql or self.command or ""}
        if self.tool_name in {
            "http_api_request",
            "database_api_request",
            "bigdata_api_request",
            "middleware_api_request",
            "discovery_api_request",
            "container_api_request",
            "network_api_request",
            "security_api_request",
            "cicd_api_request",
            "ai_platform_api_request",
            "oob_api_request",
            "k8s_api_request",
            "monitoring_api_query",
            "virtualization_api_request",
            "storage_api_request",
            "service_probe_request",
        }:
            return {
                "method": (self.method or "GET").upper(),
                "path": self.path or self.command or "/",
                "oid": self.oid or "",
                "body": self.body or {},
            }
        if self.tool_name == "evolve_skill":
            return {"skill_id": self.command or "", "file_name": self.path or ""}
        if self.tool_name == "snmp_get":
            return {"oid": self.oid or self.command or self.path or ""}
        return {"command": self.command or self.sql or self.path or ""}

    def context(self) -> dict:
        return {
            "allow_modifications": self.allow_modifications,
            "asset_type": self.asset_type or "",
            "protocol": self.protocol or "",
            "host": self.host or "",
            "trigger_source": self.trigger_source or "chat",
            "tags": self.tags,
        }


@router.get("/config/safety-policy", response_model=ResponseModel)
async def get_safety_policy_endpoint():
    from core.safety_policy import get_safety_policy

    return ResponseModel(status="success", data={"policy": get_safety_policy()})


@router.post("/config/safety-policy", response_model=ResponseModel)
async def update_safety_policy_endpoint(req: SafetyPolicyUpdateRequest):
    from core.safety_policy import save_safety_policy

    try:
        policy = save_safety_policy(req.policy)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("保存安全策略失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存安全策略失败: {e}")
    return ResponseModel(status="success", message="安全策略已保存", data={"policy": policy})


@router.post("/config/safety-policy/test", response_model=ResponseModel)
async def test_safety_policy_endpoint(req: SafetyPolicyTestRequest):
    from core.safety_policy import explain_policy_decision

    result = explain_policy_decision(req.tool_name, req.tool_args(), req.context())
    return ResponseModel(status="success", data={"result": result})

