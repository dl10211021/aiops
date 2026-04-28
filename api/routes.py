from fastapi import APIRouter, HTTPException
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
from core.skill_lifecycle import validate_skill_candidate
from core.tool_registry import tool_registry

import logging
import asyncio
import os
import json
import re
import time
from pathlib import Path

webhook_locks = {}
logger = logging.getLogger(__name__)
CUSTOM_SKILLS_DIR = Path(__file__).resolve().parent.parent / "my_custom_skills"

router = APIRouter()


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
    active_skills: list[str] = []  # 增加用户动态勾选的技能包 ID 列表
    agent_profile: str = "default"  # [OpenClaw] Agent 身份/工作区
    remark: str | None = ""  # [新功能] 连接备注/别名
    asset_type: str = "ssh"  # 资产子类型，如 linux/mysql/zabbix
    protocol: str | None = None  # 登录协议，如 ssh/winrm/mysql/http_api/snmp
    extra_args: dict = {}  # [新功能] 扩展参数，比如 db_name, api_key 等
    tags: list[str] = ["未分组"]  # [新功能] 资产组别

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
        if asset_type == "snmp":
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
                or self.extra_args.get("database")
                or self.extra_args.get("db_name")
            ):
                raise ValueError(
                    "oracle connection requires SID/service_name/database/db_name in extra_args"
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


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model_name: Optional[str] = None
    thinking_mode: Optional[str] = "off"


class ResponseModel(BaseModel):
    status: str
    data: dict = {}
    message: str = ""


class AssetPayload(BaseModel):
    remark: str | None = ""
    host: str
    port: int = 22
    username: str = ""
    password: str | None = ""
    asset_type: str = "linux"
    protocol: str | None = None
    agent_profile: str = "default"
    extra_args: dict = {}
    skills: list[str] = []
    tags: list[str] = ["未分组"]


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
    args: dict = {}


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
        return "http_api_request", {"method": method, "path": path}
    if protocol == "snmp":
        return "snmp_get", {"oid": command}

    raise HTTPException(
        status_code=400,
        detail=f"/execute 不支持 {asset_type}/{protocol}；请使用聊天会话原生工具或巡检接口。",
    )


def _category_label(category: str) -> str:
    labels = {
        "os": "操作系统与主机",
        "container": "容器与云原生",
        "db": "数据库与缓存",
        "middleware": "中间件",
        "network": "网络与安全",
        "virtualization": "虚拟化与私有云",
        "storage": "存储与备份",
        "monitor": "监控与告警",
        "oob": "硬件带外",
        "security": "安全与身份",
    }
    return labels.get(category, category.upper())


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

    return StreamingResponse(
        chat_stream_agent(
            session_id=req.session_id,
            user_message=req.message,
            model_name=req.model_name,
            thinking_mode=req.thinking_mode or "off",
        ),
        media_type="text/event-stream",
    )


class ToolApprovalRequest(BaseModel):
    tool_call_id: str
    approved: bool
    auto_approve_all: bool = False
    operator: str | None = "user"
    note: str | None = ""


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
            return ResponseModel(
                status="error", message=f"[FAIL] SSH Test Failed: {str(e)}"
            )

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
        return ResponseModel(
            status="error", message=f"[FAIL] WinRM Test Failed: {res.get('error') or res.get('output')}"
        )

    # Database Test
    requested_db_type = req.extra_args.get("db_type") if req.extra_args else None
    if login_protocol in SQL_PROTOCOLS or requested_db_type in SQL_PROTOCOLS:
        from connections.db_manager import db_executor

        db_type = req.extra_args.get("db_type") or login_protocol or "mysql"
        database = (
            req.extra_args.get("SID")
            or req.extra_args.get("service_name")
            or req.extra_args.get("database")
            or req.extra_args.get("db_name")
            or ""
        )
        # Simple heartbeat SQL
        sql = "SELECT 1 FROM DUAL" if db_type == "oracle" else "SELECT 1"

        res_str = await asyncio.to_thread(
            db_executor.execute_query,
            db_type,
            req.host,
            req.port,
            req.username,
            restored_password,
            database,
            sql,
        )
        import json

        res = json.loads(res_str)
        if res.get("success"):
            return ResponseModel(
                status="success",
                message=f"[OK] Database ({db_type.upper()}) Connection Successful!",
            )
        else:
            return ResponseModel(
                status="error",
                message=f"[FAIL] Database Connection Failed: {res.get('error')}",
            )

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
        return ResponseModel(status="error", message=f"[FAIL] Redis Test Failed: {res.get('error')}")

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
        return ResponseModel(status="error", message=f"[FAIL] MongoDB Test Failed: {res.get('error')}")

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
            return ResponseModel(
                status="error", message=f"[FAIL] TCP Connect Failed: {str(e)}"
            )

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
        return ResponseModel(status="error", message=result.get("message", "连接失败"))

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
        raise HTTPException(status_code=401, detail=result["message"])

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


def _env_or_existing(value: str, env_key: str) -> str:
    if value == "********":
        return os.environ.get(env_key, "")
    return value


@router.get("/config/notifications", response_model=ResponseModel)
async def get_notification_config():
    """【新功能】获取当前的告警通道配置"""
    import os

    return ResponseModel(
        status="success",
        data={
            "wechat_enabled": os.environ.get("WECHAT_ENABLED", "1") == "1",
            "wechat_webhook": "********" if os.environ.get("WECHAT_WEBHOOK_URL") else "",
            "dingtalk_enabled": os.environ.get("DINGTALK_ENABLED", "1") == "1",
            "dingtalk_webhook": "********" if os.environ.get("DINGTALK_WEBHOOK_URL") else "",
            "email_enabled": os.environ.get("EMAIL_ENABLED", "1") == "1",
            "email_address": os.environ.get("ALERT_EMAIL_ADDRESS", ""),
            "smtp_server": os.environ.get("SMTP_SERVER", ""),
            "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
            "smtp_user": os.environ.get("SMTP_USER", ""),
            "smtp_pass": "********" if os.environ.get("SMTP_PASS") else "",
        },
    )


@router.post("/config/notifications", response_model=ResponseModel)
async def update_notification_config(req: NotificationConfigRequest):
    """【新功能】前端动态配置企业微信/钉钉告警机器人 Webhook 及邮件"""
    import os

    os.environ["WECHAT_ENABLED"] = "1" if req.wechat_enabled else "0"
    os.environ["WECHAT_WEBHOOK_URL"] = _env_or_existing(req.wechat_webhook, "WECHAT_WEBHOOK_URL")
    os.environ["DINGTALK_ENABLED"] = "1" if req.dingtalk_enabled else "0"
    os.environ["DINGTALK_WEBHOOK_URL"] = _env_or_existing(req.dingtalk_webhook, "DINGTALK_WEBHOOK_URL")
    os.environ["EMAIL_ENABLED"] = "1" if req.email_enabled else "0"
    os.environ["ALERT_EMAIL_ADDRESS"] = req.email_address
    os.environ["SMTP_SERVER"] = req.smtp_server
    os.environ["SMTP_PORT"] = str(req.smtp_port)
    os.environ["SMTP_USER"] = req.smtp_user
    os.environ["SMTP_PASS"] = _env_or_existing(req.smtp_pass, "SMTP_PASS")

    # Optional: Write to .env file for persistence
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        # Filter out old keys
        keys_to_filter = [
            "WECHAT_ENABLED=",
            "WECHAT_WEBHOOK_URL=",
            "DINGTALK_ENABLED=",
            "DINGTALK_WEBHOOK_URL=",
            "EMAIL_ENABLED=",
            "ALERT_EMAIL_ADDRESS=",
            "SMTP_SERVER=",
            "SMTP_PORT=",
            "SMTP_USER=",
            "SMTP_PASS=",
        ]
        env_lines = [
            line
            for line in env_lines
            if not any(line.startswith(k) for k in keys_to_filter)
        ]

        env_lines.append(f"WECHAT_ENABLED={'1' if req.wechat_enabled else '0'}\n")
        env_lines.append(f"WECHAT_WEBHOOK_URL={os.environ['WECHAT_WEBHOOK_URL']}\n")
        env_lines.append(f"DINGTALK_ENABLED={'1' if req.dingtalk_enabled else '0'}\n")
        env_lines.append(f"DINGTALK_WEBHOOK_URL={os.environ['DINGTALK_WEBHOOK_URL']}\n")
        env_lines.append(f"EMAIL_ENABLED={'1' if req.email_enabled else '0'}\n")
        env_lines.append(f"ALERT_EMAIL_ADDRESS={req.email_address}\n")
        env_lines.append(f"SMTP_SERVER={req.smtp_server}\n")
        env_lines.append(f"SMTP_PORT={req.smtp_port}\n")
        env_lines.append(f"SMTP_USER={req.smtp_user}\n")
        env_lines.append(f"SMTP_PASS={os.environ['SMTP_PASS']}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
    except Exception as e:
        logger.error(f"Failed to save .env file: {e}")

    logger.info("Notification Webhooks updated.")
    return ResponseModel(status="success", message="告警通道配置已保存并生效")


class TestNotificationRequest(BaseModel):
    channel: str  # "wechat", "dingtalk", "email"


@router.post("/config/notifications/test", response_model=ResponseModel)
async def test_notification_channel(req: TestNotificationRequest):
    """【新功能】测试通知渠道"""
    channel = req.channel
    wechat_webhook = os.environ.get("WECHAT_WEBHOOK_URL", "")
    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    email_address = os.environ.get("ALERT_EMAIL_ADDRESS", "")
    smtp_server = os.environ.get("SMTP_SERVER", "")
    smtp_port = int(os.environ.get("SMTP_PORT", 465) or 465)
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    import urllib.request
    import json
    import datetime

    title = "SkillOps 平台连通性测试"
    content = f"这是一条来自 SkillOps 平台的测试消息。如果您看到此消息，说明告警通道配置正常。\n\n**发送时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        if channel == "wechat":
            if not wechat_webhook:
                raise HTTPException(status_code=400, detail="请先配置企业微信 Webhook 地址")
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": f"## {title}\n{content}"},
            }
            req_http = urllib.request.Request(
                wechat_webhook,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req_http, timeout=5)
            return ResponseModel(
                status="success", message="企业微信测试消息发送成功！请查看您的群组。"
            )

        elif channel == "dingtalk":
            if not dingtalk_webhook:
                raise HTTPException(status_code=400, detail="请先配置钉钉 Webhook 地址")
            payload = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"## {title}\n{content}"},
            }
            req_http = urllib.request.Request(
                dingtalk_webhook,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req_http, timeout=5)
            return ResponseModel(
                status="success", message="钉钉测试消息发送成功！请查看您的群组。"
            )

        elif channel == "email":
            if not email_address:
                raise HTTPException(status_code=400, detail="请先配置接收人邮箱地址")
            if not smtp_server or not smtp_user or not smtp_pass:
                raise HTTPException(
                    status_code=400,
                    detail="发送失败：尚未配置完整的 SMTP 发件服务器参数。",
                )

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = email_address
            msg["Subject"] = title
            msg.attach(MIMEText(content, "plain", "utf-8"))

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()

            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email_address, msg.as_string())
            server.quit()

            return ResponseModel(
                status="success", message=f"测试邮件已成功发送至 {email_address}！"
            )
        else:
            raise HTTPException(status_code=422, detail="不支持的渠道类型")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"测试发送失败: {str(e)}") from e


@router.put("/session/{session_id}/permission", response_model=ResponseModel)
async def update_session_permission(session_id: str, req: PermissionUpdateRequest):
    """【新功能】动态提权/降权：在不中断 SSH 的情况下，修改当前会话的 AI 修改权限"""
    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    ssh_manager.active_sessions[session_id]["info"]["allow_modifications"] = (
        req.allow_modifications
    )
    logger.info(
        f"Session {session_id} permissions changed to: {req.allow_modifications}"
    )

    return ResponseModel(status="success", message="权限已实时更新")


@router.put("/session/{session_id}/heartbeat", response_model=ResponseModel)
async def update_session_heartbeat(session_id: str, req: HeartbeatUpdateRequest):
    """【新功能】动态开启或关闭心跳巡检"""
    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    ssh_manager.active_sessions[session_id]["info"]["heartbeat_enabled"] = (
        req.heartbeat_enabled
    )
    if req.heartbeat_enabled:
        ssh_manager.active_sessions[session_id]["info"]["last_active"] = (
            0  # Trigger immediately on next poll
        )

    if req.master_interval is not None:
        if "extra_args" not in ssh_manager.active_sessions[session_id]["info"]:
            ssh_manager.active_sessions[session_id]["info"]["extra_args"] = {}
        ssh_manager.active_sessions[session_id]["info"]["extra_args"][
            "master_interval"
        ] = req.master_interval
        logger.info(
            f"Session {session_id} master_interval updated to: {req.master_interval}s"
        )

    logger.info(f"Session {session_id} heartbeat changed to: {req.heartbeat_enabled}")

    return ResponseModel(status="success", message="心跳巡检状态已更新")


@router.get("/sessions/poll_all", response_model=ResponseModel)
async def poll_all_sessions_messages():
    """【新功能】全局长轮询获取所有后台会话的待推送消息，极大地降低大规模纳管时的请求数量"""
    updates = {}
    with ssh_manager._sessions_lock:
        for session_id, sdata in ssh_manager.active_sessions.items():
            pending = sdata["info"].get("pending_messages", [])
            if pending:
                updates[session_id] = pending.copy()
                sdata["info"]["pending_messages"] = []

    return ResponseModel(status="success", data={"updates": updates})


@router.get("/session/{session_id}/poll", response_model=ResponseModel)
async def poll_session_messages(session_id: str):
    """【新功能】前端长轮询获取后台心跳主动推送的消息"""
    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="Session disconnected")

    with ssh_manager._sessions_lock:
        pending = ssh_manager.active_sessions[session_id]["info"].get(
            "pending_messages", []
        )
        if pending:
            ssh_manager.active_sessions[session_id]["info"]["pending_messages"] = []
            return ResponseModel(status="success", data={"messages": pending})

    return ResponseModel(status="success", data={"messages": []})


@router.get("/session/{session_id}/history", response_model=ResponseModel)
async def get_session_history(session_id: str):
    """【新功能】获取会话的历史消息记录，用于前端恢复"""
    from core.memory import memory_db

    try:
        messages = memory_db.get_messages(session_id, for_ui=True)
        # 过滤掉系统提示词，只返回对用户有意义的历史
        chat_history = [
            msg for msg in messages if msg.get("role") in ("user", "assistant")
        ]
        return ResponseModel(status="success", data={"messages": chat_history})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/session/{session_id}/history", response_model=ResponseModel)
async def delete_session_history(session_id: str):
    """【新功能】清空会话的聊天记录"""
    from core.memory import memory_db

    try:
        memory_db.clear_history(session_id)
        return ResponseModel(status="success", message="会话记录已清空")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/session/{session_id}/skills", response_model=ResponseModel)
async def update_session_skills(session_id: str, req: SkillsUpdateRequest):
    """【新功能】动态修改挂载技能包：在不中断会话的情况下，挂载或卸载 AI 技能"""
    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    ssh_manager.active_sessions[session_id]["info"]["active_skills"] = req.active_skills
    logger.info(f"Session {session_id} active skills changed to: {req.active_skills}")

    return ResponseModel(status="success", message="挂载技能已实时更新")


@router.get("/sessions/active", response_model=ResponseModel)
async def get_active_sessions():
    """【新功能】前端刷新页面时同步当前后端的活跃会话"""
    sessions_data = {}
    for sid, sdata in list(ssh_manager.active_sessions.items()):
        info = sdata["info"]
        identity = resolve_asset_identity(
            info.get("asset_type"),
            info.get("protocol"),
            info.get("extra_args", {}),
            info.get("host"),
            info.get("port"),
            info.get("remark"),
        )
        protocol = identity["protocol"]
        sessions_data[sid] = {
            "id": sid,
            "host": info.get("host"),
            "remark": info.get("remark"),
            "isReadWriteMode": info.get("allow_modifications"),
            "skills": info.get("active_skills", []),
            "agentProfile": info.get("agent_profile"),
            "user": info.get("username"),
            "asset_type": identity["asset_type"],
            "protocol": protocol,
            "extra_args": identity["extra_args"],
            "heartbeatEnabled": info.get("heartbeat_enabled", False),
            "tags": info.get("tags", ["未分组"]),
            "target_scope": info.get("target_scope", "asset"),
            "scope_value": info.get("scope_value"),
        }

    from core.memory import memory_db

    for sid, s_data in sessions_data.items():
        if s_data.get("extra_args"):
            for k in memory_db.sensitive_keys:
                if k in s_data["extra_args"] and s_data["extra_args"][k]:
                    s_data["extra_args"][k] = "********"
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
    from core.slash_commands import render_slash_commands

    if session_id not in ssh_manager.active_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已断开")

    tools_response = await get_session_tools(session_id)
    commands = render_slash_commands(
        tools_response.data["context"],
        tools_response.data.get("active_tools") or [],
    )
    return ResponseModel(status="success", data={"commands": commands})


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
    for a in assets:
        if a.get("password"):
            a["password"] = "********"
        if "extra_args" in a and a["extra_args"]:
            for k in memory_db.sensitive_keys:
                if k in a["extra_args"] and a["extra_args"][k]:
                    a["extra_args"][k] = "********"
    return ResponseModel(status="success", data={"assets": assets})


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
    types = get_asset_catalog()
    categories = []
    seen = set()
    for item in types:
        category = item.get("category") or "other"
        if category in seen:
            continue
        seen.add(category)
        categories.append({"id": category, "label": _category_label(category)})
    return ResponseModel(status="success", data={"types": types, "categories": categories})


@router.get("/assets/types", response_model=ResponseModel)
async def get_asset_types():
    """返回后端认可的资产类型与默认登录协议目录。"""
    return _asset_types_response()


@router.get("/assets/{asset_id}", response_model=ResponseModel)
async def get_asset(asset_id: int):
    """查询单个资产详情；响应会脱敏密码和敏感 extra_args。"""
    from core.memory import memory_db

    asset = await asyncio.to_thread(memory_db.get_asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.get("password"):
        asset["password"] = "********"
    if "extra_args" in asset and asset["extra_args"]:
        for k in memory_db.sensitive_keys:
            if k in asset["extra_args"] and asset["extra_args"][k]:
                asset["extra_args"][k] = "********"
    return ResponseModel(status="success", data={"asset": asset})


@router.put("/assets/{asset_id}", response_model=ResponseModel)
async def update_asset(asset_id: int, req: AssetPayload):
    """按资产 ID 修改资产；传入 ******** 会保留原密码/密钥。"""
    from core.memory import memory_db

    asset = await asyncio.to_thread(memory_db.update_asset, asset_id, req.model_dump())
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.get("password"):
        asset["password"] = "********"
    if "extra_args" in asset and asset["extra_args"]:
        for k in memory_db.sensitive_keys:
            if k in asset["extra_args"] and asset["extra_args"][k]:
                asset["extra_args"][k] = "********"
    return ResponseModel(status="success", message="资产已更新", data={"asset": asset})


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
    by_category: dict[str, int] = {}
    by_protocol: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for asset in assets:
        identity = resolve_asset_identity(
            asset.get("asset_type"),
            asset.get("protocol"),
            asset.get("extra_args", {}),
            asset.get("host"),
            asset.get("port"),
            asset.get("remark"),
        )
        category = identity.get("category") or "other"
        by_category[category] = by_category.get(category, 0) + 1
        by_protocol[identity["protocol"]] = by_protocol.get(identity["protocol"], 0) + 1
        by_type[identity["asset_type"]] = by_type.get(identity["asset_type"], 0) + 1

    active_by_protocol: dict[str, int] = {}
    for item in active:
        info = item.get("info", {})
        protocol = resolve_asset_identity(
            info.get("asset_type"),
            info.get("protocol"),
            info.get("extra_args", {}),
            info.get("host"),
            info.get("port"),
            info.get("remark"),
        )["protocol"]
        active_by_protocol[protocol] = active_by_protocol.get(protocol, 0) + 1

    return ResponseModel(
        status="success",
        data={
            "summary": {
                "asset_total": len(assets),
                "active_sessions": len(active),
                "asset_categories": len(by_category),
                "protocols": len(by_protocol),
            },
            "by_category": by_category,
            "by_protocol": by_protocol,
            "by_type": by_type,
            "active_by_protocol": active_by_protocol,
            "alerts": alert_summary(),
            "jobs": {
                "total": len(CronManager.get_all_jobs()),
                "scheduled": sum(1 for job in CronManager.get_all_jobs() if job.get("status") == "scheduled"),
                "paused": sum(1 for job in CronManager.get_all_jobs() if job.get("status") == "paused"),
            },
            "inspection_runs": run_summary(),
        },
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

    buckets: dict[str, dict[str, int]] = {}
    for alert in list_alert_events(limit=5000):
        day = str(alert.get("created_at") or "")[:10] or "unknown"
        severity = str(alert.get("severity") or "unknown").lower()
        bucket = buckets.setdefault(day, {"date": day, "total": 0})
        bucket["total"] += 1
        bucket[severity] = bucket.get(severity, 0) + 1
    points = [buckets[key] for key in sorted(buckets)]
    return ResponseModel(status="success", data={"points": points})


@router.get("/dashboard/risk-ranking", response_model=ResponseModel)
async def get_dashboard_risk_ranking():
    """大屏风险排行接口，当前按告警数量和严重度聚合主机风险。"""
    from core.alert_events import list_alert_events

    weights = {"critical": 5, "fatal": 5, "error": 4, "warning": 2, "warn": 2, "info": 1}
    by_host: dict[str, dict[str, int | str]] = {}
    for alert in list_alert_events(limit=5000):
        host = str(alert.get("host") or "unknown")
        severity = str(alert.get("severity") or "info").lower()
        item = by_host.setdefault(host, {"host": host, "count": 0, "score": 0})
        item["count"] = int(item["count"]) + 1
        item["score"] = int(item["score"]) + weights.get(severity, 1)
    ranking = sorted(by_host.values(), key=lambda item: (int(item["score"]), int(item["count"])), reverse=True)[:20]
    return ResponseModel(status="success", data={"ranking": ranking})


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
    extra_args: dict = {}
    skills: list[str] = []
    tags: list[str] = ["未分组"]


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
        messages = memory_db.get_messages(session_id, for_ui=True)
        chat_history = [
            msg for msg in messages if msg.get("role") in ("user", "assistant")
        ]
        if not chat_history:
            raise HTTPException(status_code=404, detail="该会话没有可导出的历史记录。")

        remark = ""
        if session_id in ssh_manager.active_sessions:
            remark = ssh_manager.active_sessions[session_id]["info"].get("remark", "")

        md_lines = [f"# Chat History: {remark or session_id}\n"]
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "AI Assistant"
            md_lines.append(f"## {role}\n{msg['content']}\n\n---\n")

        return ResponseModel(status="success", data={"markdown": "\n".join(md_lines)})
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


@router.get("/config/safety-policy", response_model=ResponseModel)
async def get_safety_policy_endpoint():
    from core.safety_policy import get_safety_policy

    return ResponseModel(status="success", data={"policy": get_safety_policy()})


@router.post("/config/safety-policy", response_model=ResponseModel)
async def update_safety_policy_endpoint(req: SafetyPolicyUpdateRequest):
    from core.safety_policy import save_safety_policy

    try:
        policy = save_safety_policy(req.policy)
    except Exception as e:
        logger.error("保存安全策略失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存安全策略失败: {e}")
    return ResponseModel(status="success", message="安全策略已保存", data={"policy": policy})

