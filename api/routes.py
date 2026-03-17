from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from connections.ssh_manager import ssh_manager
from fastapi.responses import StreamingResponse
from core.agent import chat_stream_agent

import logging
import asyncio
import os

logger = logging.getLogger(__name__)

router = APIRouter()


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
    protocol: str = "ssh"  # [新功能] 资产协议类型 (ssh, telnet, db, api, winrm)
    extra_args: dict = {}  # [新功能] 扩展参数，比如 db_name, api_key 等
    tags: list[str] = ["未分组"]  # [新功能] 资产组别
    target_scope: str = "asset"  # 作用域：global, group, asset
    scope_value: str | None = (
        None  # 如果 scope 为 group，则为 tag 名称；如果为 asset，为 host/id；global 为空
    )


class CommandRequest(BaseModel):
    session_id: str
    command: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model_name: str = "gemini-3.1-pro-preview"


class ResponseModel(BaseModel):
    status: str
    data: dict = {}
    message: str = ""


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
        ),
        media_type="text/event-stream",
    )


class ToolApprovalRequest(BaseModel):
    tool_call_id: str
    approved: bool
    auto_approve_all: bool = False


@router.post("/session/{session_id}/approve", response_model=ResponseModel)
async def approve_tool_call(session_id: str, req: ToolApprovalRequest):
    """【新功能】用户确认是否允许 AI 执行敏感指令"""
    from core.dispatcher import dispatcher
    from connections.ssh_manager import ssh_manager

    if req.auto_approve_all:
        if session_id in ssh_manager.active_sessions:
            ssh_manager.active_sessions[session_id]["info"]["auto_approve_all"] = True
            logger.info(f"Session {session_id} set to auto-approve all tools.")

    future = dispatcher.pending_approvals.get(req.tool_call_id)
    if future and not future.done():
        future.set_result(req.approved)
        return ResponseModel(status="success", message="Approval action submitted.")

    return ResponseModel(
        status="error", message="Pending tool call not found or already processed."
    )


@router.post("/session/{session_id}/stop", response_model=ResponseModel)
async def stop_chat_session(session_id: str):
    """【新功能】终止当前会话中正在生成的长流响应/执行任务"""
    from core.agent import cancel_flags

    cancel_flags[session_id] = True
    return ResponseModel(status="success", message="已发送中止信号。")


@router.post("/connect/test", response_model=ResponseModel)
async def test_connection(req: ConnectionRequest):
    import asyncio
    import os

    # SSH Test
    if req.protocol == "ssh":
        from connections.ssh_manager import ssh_manager

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
                password=req.password,
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

    # Database Test
    if (
        req.protocol == "database"
        or "database" in str(req.active_skills)
        or (req.extra_args and req.extra_args.get("db_type"))
    ):
        from connections.db_manager import db_executor

        db_type = req.extra_args.get("db_type", "mysql")
        database = req.extra_args.get("SID") or req.extra_args.get("database") or ""
        # Simple heartbeat SQL
        sql = "SELECT 1 FROM DUAL" if db_type == "oracle" else "SELECT 1"

        res_str = await asyncio.to_thread(
            db_executor.execute_query,
            db_type,
            req.host,
            req.port,
            req.username,
            req.password,
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

    # API / Virtual Test: Ping
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


@router.post("/connect", response_model=ResponseModel)
async def create_ssh_connection(req: ConnectionRequest):
    """建立与远程系统的会话 (支持 SSH长连接 或 虚拟凭据会话)"""
    logger.info(
        f"API called: Connect to {req.host} via {req.protocol} with profile {req.agent_profile}, remark: {req.remark}"
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
        password=req.password,
        key_filename=key_path,
        allow_modifications=req.allow_modifications,
        active_skills=req.active_skills,  # 透传给底层会话
        agent_profile=req.agent_profile,  # 透传 Agent 身份
        remark=req.remark,  # 透传备注
        protocol=req.protocol,  # 透传协议
        extra_args=req.extra_args,  # 透传扩展凭证 (API Key, DB Name 等)
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
            password=req.password,
            protocol=req.protocol,
            agent_profile=req.agent_profile,
            extra_args=req.extra_args,
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
    logger.info(f"API called: Executing '{req.command}' on session {req.session_id}")

    # 解决同步下发指令卡死 FastAPI 问题
    result = await asyncio.to_thread(
        ssh_manager.execute_command, session_id=req.session_id, command=req.command
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return ResponseModel(
        status="success",
        data={
            "output": result["output"],
            "has_error": result["has_error"],
            "exit_status": result["exit_status"],
        },
    )


class PermissionUpdateRequest(BaseModel):
    allow_modifications: bool


class HeartbeatUpdateRequest(BaseModel):
    heartbeat_enabled: bool
    master_interval: int | None = None


class SkillsUpdateRequest(BaseModel):
    active_skills: list[str]


class LLMConfigRequest(BaseModel):
    base_url: str
    api_key: str


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


class CreateSkillRequest(BaseModel):
    skill_id: str
    description: str
    instructions: str
    script_name: str | None = None
    script_content: str | None = None


@router.post("/skills/create", response_model=ResponseModel)
async def create_skill(req: CreateSkillRequest):
    """【新功能】用户在页面上手动创建新的定制技能卡带"""
    import os

    # 强制校验 ID 格式 (只能包含英文字母、数字和横线)
    import re

    if not re.match(r"^[a-zA-Z0-9\-]+$", req.skill_id):
        return ResponseModel(
            status="error",
            message="技能 ID 只能包含英文字母、数字和横线 (如 my-first-skill)。",
        )

    target_base = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
    )
    os.makedirs(target_base, exist_ok=True)

    dest_path = os.path.join(target_base, req.skill_id)

    try:
        if os.path.exists(dest_path):
            return ResponseModel(
                status="error",
                message=f"该技能包 ID ({req.skill_id}) 已存在，请换一个名称。",
            )

        os.makedirs(dest_path)

        # 写入 SKILL.md
        md_content = f"---\nname: {req.skill_id}\ndescription: {req.description}\n---\n\n{req.instructions}\n"
        with open(os.path.join(dest_path, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(md_content)

        # 如果提供了脚本内容，一并写入
        if req.script_name and req.script_content:
            safe_script_name = os.path.basename(req.script_name)
            script_path = os.path.join(dest_path, safe_script_name)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(req.script_content)

        # 通知 Dispatcher 重新加载
        from core.dispatcher import dispatcher

        dispatcher.refresh_skills(force=True)

        return ResponseModel(
            status="success",
            message=f"全新定制技能 {req.skill_id} 创建成功，已自动加载就绪！",
        )
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


@router.post("/skills/migrate", response_model=ResponseModel)
async def migrate_skill(req: MigrateRequest):
    """将外部卡带拷贝到专属的 my_custom_skills 目录"""
    import shutil
    import os

    target_base = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
    )
    os.makedirs(target_base, exist_ok=True)

    dest_path = os.path.join(target_base, req.target_dir_name)

    try:
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)

        shutil.copytree(req.source_path, dest_path)

        # 拷贝完成后通知 Dispatcher 重新加载
        from core.dispatcher import dispatcher

        dispatcher.refresh_skills(force=True)

        return ResponseModel(
            status="success", message=f"卡带 {req.target_dir_name} 已成功导入专属库！"
        )
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


@router.get("/config/models", response_model=ResponseModel)
async def get_models():
    # Dynamic fetch of models
    from core.agent import get_available_models

    models = await get_available_models()
    if models:
        return ResponseModel(status="success", data={"models": models})
    else:
        return ResponseModel(status="error", message="Cannot fetch models.")


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
            "api_key": os.environ.get("OPENAI_API_KEY", api_key),
        },
    )


@router.post("/config/llm", response_model=ResponseModel)
async def update_llm_config(req: LLMConfigRequest):
    """【新功能】前端动态覆盖大模型底层的 Base_URL 和 Key"""
    # 动态重载 Agent 的配置
    from core.agent import update_client_config
    import os

    try:
        update_client_config(req.base_url, req.api_key)
        logger.info(f"LLM Client Config dynamically updated via API.")

        # 将配置持久化到 .env 文件中
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        keys_to_filter = ["OPENAI_API_KEY=", "OPENAI_BASE_URL="]
        env_lines = [
            line
            for line in env_lines
            if not any(line.startswith(k) for k in keys_to_filter)
        ]

        env_lines.append(f"OPENAI_BASE_URL={req.base_url}\n")
        env_lines.append(f"OPENAI_API_KEY={req.api_key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)

        return ResponseModel(
            status="success", message="AI 大脑已重新连接，并已保存为默认配置"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/config/notifications", response_model=ResponseModel)
async def get_notification_config():
    """【新功能】获取当前的告警通道配置"""
    import os

    return ResponseModel(
        status="success",
        data={
            "wechat_enabled": os.environ.get("WECHAT_ENABLED", "1") == "1",
            "wechat_webhook": os.environ.get("WECHAT_WEBHOOK_URL", ""),
            "dingtalk_enabled": os.environ.get("DINGTALK_ENABLED", "1") == "1",
            "dingtalk_webhook": os.environ.get("DINGTALK_WEBHOOK_URL", ""),
            "email_enabled": os.environ.get("EMAIL_ENABLED", "1") == "1",
            "email_address": os.environ.get("ALERT_EMAIL_ADDRESS", ""),
            "smtp_server": os.environ.get("SMTP_SERVER", ""),
            "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
            "smtp_user": os.environ.get("SMTP_USER", ""),
            "smtp_pass": os.environ.get("SMTP_PASS", ""),
        },
    )


@router.post("/config/notifications", response_model=ResponseModel)
async def update_notification_config(req: NotificationConfigRequest):
    """【新功能】前端动态配置企业微信/钉钉告警机器人 Webhook 及邮件"""
    import os

    os.environ["WECHAT_ENABLED"] = "1" if req.wechat_enabled else "0"
    os.environ["WECHAT_WEBHOOK_URL"] = req.wechat_webhook
    os.environ["DINGTALK_ENABLED"] = "1" if req.dingtalk_enabled else "0"
    os.environ["DINGTALK_WEBHOOK_URL"] = req.dingtalk_webhook
    os.environ["EMAIL_ENABLED"] = "1" if req.email_enabled else "0"
    os.environ["ALERT_EMAIL_ADDRESS"] = req.email_address
    os.environ["SMTP_SERVER"] = req.smtp_server
    os.environ["SMTP_PORT"] = str(req.smtp_port)
    os.environ["SMTP_USER"] = req.smtp_user
    os.environ["SMTP_PASS"] = req.smtp_pass

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
        env_lines.append(f"WECHAT_WEBHOOK_URL={req.wechat_webhook}\n")
        env_lines.append(f"DINGTALK_ENABLED={'1' if req.dingtalk_enabled else '0'}\n")
        env_lines.append(f"DINGTALK_WEBHOOK_URL={req.dingtalk_webhook}\n")
        env_lines.append(f"EMAIL_ENABLED={'1' if req.email_enabled else '0'}\n")
        env_lines.append(f"ALERT_EMAIL_ADDRESS={req.email_address}\n")
        env_lines.append(f"SMTP_SERVER={req.smtp_server}\n")
        env_lines.append(f"SMTP_PORT={req.smtp_port}\n")
        env_lines.append(f"SMTP_USER={req.smtp_user}\n")
        env_lines.append(f"SMTP_PASS={req.smtp_pass}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
    except Exception as e:
        logger.error(f"Failed to save .env file: {e}")

    logger.info(f"Notification Webhooks updated.")
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
                return ResponseModel(
                    status="error", message="请先配置企业微信 Webhook 地址"
                )
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
                return ResponseModel(
                    status="error", message="请先配置钉钉 Webhook 地址"
                )
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
                return ResponseModel(status="error", message="请先配置接收人邮箱地址")
            if not smtp_server or not smtp_user or not smtp_pass:
                return ResponseModel(
                    status="error",
                    message="发送失败：尚未配置完整的 SMTP 发件服务器参数。",
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
            return ResponseModel(status="error", message="不支持的渠道类型")
    except Exception as e:
        return ResponseModel(status="error", message=f"测试发送失败: {str(e)}")


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
        return ResponseModel(status="error", message="Session disconnected")

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
        return ResponseModel(status="error", message=str(e))


@router.delete("/session/{session_id}/history", response_model=ResponseModel)
async def delete_session_history(session_id: str):
    """【新功能】清空会话的聊天记录"""
    from core.memory import memory_db

    try:
        memory_db.clear_history(session_id)
        return ResponseModel(status="success", message="会话记录已清空")
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


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
        sessions_data[sid] = {
            "id": sid,
            "host": info.get("host"),
            "remark": info.get("remark"),
            "isReadWriteMode": info.get("allow_modifications"),
            "skills": info.get("active_skills", []),
            "agentProfile": info.get("agent_profile"),
            "user": info.get("username"),
            "protocol": info.get("protocol"),
            "extra_args": info.get("extra_args", {}),
            "heartbeatEnabled": info.get("heartbeat_enabled", False),
            "tags": info.get("tags", ["未分组"]),
        }
    return ResponseModel(status="success", data={"sessions": sessions_data})


@router.delete("/disconnect/{session_id}", response_model=ResponseModel)
async def close_ssh_connection(session_id: str):
    """大模型或者前端关闭会话释放资源"""
    success = await asyncio.to_thread(ssh_manager.disconnect, session_id)
    if not success:
        return ResponseModel(status="error", message="Session not found")

    return ResponseModel(status="success", message="Connection closed safely")


@router.get("/assets/saved", response_model=ResponseModel)
async def get_saved_assets():
    """【新功能】获取 SQLite 中持久化的所有资产信息（通讯录）"""
    from core.memory import memory_db

    assets = await asyncio.to_thread(memory_db.get_all_assets)
    return ResponseModel(status="success", data={"assets": assets})


@router.delete("/assets/{asset_id}", response_model=ResponseModel)
async def delete_saved_asset(asset_id: int):
    """【新功能】删除持久化的资产"""
    from core.memory import memory_db

    await asyncio.to_thread(memory_db.delete_asset, asset_id)
    return ResponseModel(status="success", message="资产已成功移除金库。")


# ----------------- OpenClaw / ManageEngine Webhook 闭环设计 -----------------
from fastapi import Request

from fastapi import UploadFile, File
import shutil


@router.post("/knowledge/upload", response_model=ResponseModel)
async def upload_knowledge_document(file: UploadFile = File(...)):
    """【新功能】上传运维文档并注入 LanceDB 知识库"""
    import os
    from core.rag import kb_manager
    from core.agent import client

    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(kb_manager.kb_dir, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        res = await kb_manager.ingest_document(file_path, client)
        if res["status"] == "success":
            return ResponseModel(status="success", message=res["message"])
        else:
            return ResponseModel(status="error", message=res["message"])
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


@router.get("/knowledge/list", response_model=ResponseModel)
async def list_knowledge_documents():
    """【新功能】列出已注入知识库的文档列表"""
    from core.rag import kb_manager

    try:
        files = await kb_manager.list_documents()
        return ResponseModel(status="success", data={"files": files})
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


@router.delete("/knowledge/{filename}", response_model=ResponseModel)
async def delete_knowledge_document(filename: str):
    """【新功能】从知识库中删除某个文档"""
    from core.rag import kb_manager

    try:
        res = await kb_manager.delete_document(filename)
        if res["status"] == "success":
            return ResponseModel(status="success", message=res["message"])
        else:
            return ResponseModel(status="error", message=res["message"])
    except Exception as e:
        return ResponseModel(status="error", message=str(e))


@router.post("/webhook/alert", response_model=ResponseModel)
async def receive_webhook_alert(request: Request):
    """【AIOps 高级特性】接收外部告警 (Prometheus / ManageEngine) 并推入相关 AI 会话"""
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        payload = {}

    logger.info(f"Raw Webhook Payload received: {payload}")

    # 兼容卓豪 (ManageEngine) 和 Prometheus 等常见告警系统的数据结构
    # 提取主机/节点信息
    host = (
        payload.get("host")
        or payload.get("node")
        or payload.get("device")
        or payload.get("MonitorName")
        or "all"
    )

    # 提取告警标题
    alert_name = (
        payload.get("alert_name")
        or payload.get("displayName")
        or payload.get("name")
        or "System Alert"
    )

    # 提取严重程度
    severity = (
        payload.get("severity")
        or payload.get("Severity")
        or payload.get("status")
        or "warning"
    )

    # 提取详情
    description = (
        payload.get("description")
        or payload.get("message")
        or payload.get("Message")
        or payload.get("AlarmMessage")
        or str(payload)
    )

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
            status="success", message="告警已接收，但目前无人值守，已记录日志。"
        )

    # 从内存中提取 Agent 的对话历史，强行塞入一条【系统通知】
    from core.memory import memory_db
    from core.dispatcher import dispatcher
    from core.heartbeat import run_single_heartbeat
    import asyncio

    injection_msg = f"🔔 【监控告警接入】外部系统触发了级别为 [{str(severity).upper()}] 的告警。\n**告警名称**：{alert_name}\n**故障节点**：{host}\n**详细信息**：\n{description}\n\n作为监控专家，请主动分析此告警。如果你是负责整个环境的指挥官（例如你的连接是 localhost），请使用 `list_active_sessions` 查找合适的子节点并使用 `delegate_task_to_agent` 派发调查任务；如果你是具体服务器的节点 Agent，请立刻调用技能/工具去探查根因！"

    injected_count = 0
    for sid in affected_sessions:
        info = ssh_manager.active_sessions[sid].get("info", {})

        # 为了避免并发冲突，简单锁一下当前 session
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
    )


# ----------------- OpenClaw 自动化巡检 (Cron Jobs) -----------------
class CronAddRequest(BaseModel):
    cron_expr: str = "0 9 * * *"
    message: str = "执行每日系统深度体检，生成资源使用率报告并发送到群组。"
    host: str
    username: str
    agent_profile: str = "default"
    password: str | None = None
    private_key_path: str | None = None


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
        )
        return ResponseModel(
            status="success", message=f"已成功添加定时巡检计划: {job_id}"
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
    except Exception as e:
        raise HTTPException(status_code=404, detail="未找到该计划。")


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
    protocol: str = "ssh"
    agent_profile: str = "default"
    extra_args: dict = {}
    skills: list[str] = []
    tags: list[str] = ["未分组"]


@router.post("/assets/batch_import", response_model=ResponseModel)
async def batch_import_assets(items: list[BatchAssetImportItem]):
    """【#25 新功能】批量导入资产到金库（通讯录），支持 JSON 数组格式"""
    from core.memory import memory_db

    imported = 0
    errors = []
    try:
        await asyncio.to_thread(
            memory_db.save_assets_batch, [item.model_dump() for item in items]
        )
        imported = len(items)
    except Exception as e:
        errors.append(str(e))

    msg = f"成功导入 {imported}/{len(items)} 条资产。"
    if errors:
        msg += f" 失败 {len(errors)} 条: {'; '.join(errors[:5])}"
    return ResponseModel(status="success" if imported > 0 else "error", message=msg)


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
            return ResponseModel(status="error", message="该会话没有可导出的历史记录。")

        remark = ""
        if session_id in ssh_manager.active_sessions:
            remark = ssh_manager.active_sessions[session_id]["info"].get("remark", "")

        md_lines = [f"# Chat History: {remark or session_id}\n"]
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "AI Assistant"
            md_lines.append(f"## {role}\n{msg['content']}\n\n---\n")

        return ResponseModel(status="success", data={"markdown": "\n".join(md_lines)})
    except Exception as e:
        return ResponseModel(status="error", message=str(e))
