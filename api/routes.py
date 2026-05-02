from fastapi import APIRouter, HTTPException, UploadFile, File
from connections.ssh_manager import ssh_manager
from fastapi.responses import StreamingResponse
from core.agent import chat_stream_agent
from api.errors import raise_http_error
from api.mappers import session_webhook_delivery_kwargs
from core.asset_protocols import (
    API_PROTOCOLS,
    SQL_PROTOCOLS,
    get_asset_catalog,
)
from core.connection_inspection_service import inspect_connection_session
from core.connection_request_service import (
    asset_matches_connection_request,
    get_login_protocol_from_request,
    restore_connection_request_secrets,
)
from core.connection_session_service import (
    ConnectionSessionServiceError,
    create_connection_session,
)
from core.connection_test_service import run_connection_test
from core.legacy_command_service import (
    LegacyCommandServiceError,
    execute_legacy_command_record,
)
from core.session_views import build_active_sessions_response
from core.skill_lifecycle import validate_skill_candidate
from core.tool_registry import tool_registry
from core.custom_skill_catalog_service import (
    CustomSkillCatalogServiceError,
    get_custom_skill_detail as get_custom_skill_detail_record,
    list_custom_skill_catalog,
    scan_custom_skill_catalog,
)
from core.custom_skill_version_service import (
    CustomSkillVersionServiceError,
    list_custom_skill_version_records,
)
from core.custom_skill_create_service import (
    CustomSkillCreateServiceError,
    create_custom_skill_record,
)
from core.custom_skill_migration_service import (
    CustomSkillMigrationServiceError,
    migrate_custom_skill_record,
)
from core.custom_skill_rollback_service import (
    CustomSkillRollbackServiceError,
    rollback_custom_skill_version as rollback_custom_skill_version_record,
)
from core.chat_attachments import (
    CHAT_ATTACHMENT_MAX_SIZE,
    ChatAttachmentError,
    build_chat_attachment_preview,
)
from core.chat_session_service import (
    ChatSessionServiceError,
    request_session_stop,
    start_session_chat_run,
)
from core.session_webhook_service import (
    SessionWebhookServiceError,
    list_session_webhook_delivery_records,
    preview_session_webhook_delivery,
    send_session_webhook_delivery,
)
from core.dashboard_service import (
    build_dashboard_alert_trend_payload,
    build_dashboard_inspection_run_trend_payload,
    build_dashboard_overview_payload,
    build_dashboard_risk_ranking_payload,
)
from core.asset_catalog_response import build_asset_types_response
from core.asset_service import (
    AssetServiceError,
    batch_import_asset_records,
    get_saved_asset_record,
    list_saved_asset_records,
    remove_saved_asset_record,
    save_asset_record,
    update_saved_asset_record,
)
from core.notification_config import (
    build_notification_config,
    save_notification_config as save_notification_config_record,
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
from core.session_history_service import (
    SessionHistoryServiceError,
    clear_session_history_messages,
    delete_session_history_message_record,
    export_session_history_markdown_record,
    list_session_history_messages,
    update_session_history_message_record,
)
from core.session_commands import (
    SessionCommandError,
    build_session_commands_response,
    list_custom_slash_commands as list_custom_slash_commands_data,
    remove_custom_slash_command,
    save_custom_slash_command,
)
from core.session_tool_context import (
    SessionToolContextError,
    build_session_tools_payload_for_session,
)
from core.inspection_template_service import (
    InspectionTemplateServiceError,
    list_inspection_template_records,
    remove_inspection_template_record,
    save_inspection_template_record,
)
from core.session_inspection_response import build_inspection_response_payload
from core.inspection_run_service import (
    InspectionRunServiceError,
    export_inspection_run_report_content,
    get_inspection_run_record,
    get_inspection_run_report_record,
    inspection_run_summary,
    list_inspection_run_records,
)
from core.inspection_job_service import (
    InspectionJobServiceError,
    create_inspection_job_record,
    list_inspection_job_records,
    pause_inspection_job_record,
    remove_inspection_job_record,
    resume_inspection_job_record,
    run_inspection_job_record_now,
    update_inspection_job_record,
)
from core.protocol_verification_service import (
    ProtocolVerificationServiceError,
    build_protocol_verification_matrix,
    build_protocol_verification_overview,
    list_protocol_verification_run_records,
    run_protocol_verification_for_asset,
)
from core.safety_policy_service import (
    SafetyPolicyServiceError,
    explain_safety_policy_test,
    get_safety_policy_record,
    save_safety_policy_record,
)
from core.provider_config_service import (
    ProviderConfigServiceError,
    list_provider_config_records,
    save_provider_config_records,
)
from core.app_config_service import (
    AppConfigServiceError,
    build_llm_config_payload,
    get_agent_runtime_config_record,
    get_embedding_config_record,
    save_agent_runtime_config_record,
    save_embedding_config_record,
)
from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    ingest_knowledge_document,
    list_knowledge_document_records,
    remove_knowledge_document_record,
)
from core.alert_webhook_service import handle_alert_webhook, read_alert_webhook_payload
from core.alert_event_service import (
    AlertEventServiceError,
    get_alert_event_record,
    list_alert_event_records,
    update_alert_event_record,
)
from core.approval_request_service import (
    ApprovalRequestServiceError,
    decide_approval_request_record,
    get_approval_request_record,
    list_approval_request_records,
)
from core.approval_execution_service import (
    ApprovalExecutionServiceError,
    execute_custom_skill_rollback_approval,
)
from core.session_interaction_service import (
    SessionInteractionServiceError,
    approve_session_tool_call,
    submit_user_interaction_response,
)
from api.schemas import (
    AgentRuntimeConfigRequest,
    AlertEventUpdateRequest,
    ApprovalDecisionRequest,
    AssetPayload,
    BatchAssetImportItem,
    ChatRequest,
    CommandRequest,
    ConnectionInspectionRequest,
    ConnectionRequest,
    CreateSkillRequest,
    CronAddRequest,
    EmbeddingConfigRequest,
    HeartbeatUpdateRequest,
    InspectionTemplatePayload,
    InspectionTemplateStepPayload,
    MigrateRequest,
    NotificationConfigRequest,
    PermissionUpdateRequest,
    ProviderConfig,
    ResponseModel,
    SafetyPolicyTestRequest,
    SafetyPolicyUpdateRequest,
    SessionGroupUpdateRequest,
    SessionMessageUpdateRequest,
    SessionProfileGenerateRequest,
    SessionWebhookSendRequest,
    SkillRollbackRequest,
    SkillsUpdateRequest,
    SkillValidationRequest,
    SlashCommandPayload,
    TestNotificationRequest,
    ToolApprovalRequest,
    UserInteractionResponseRequest,
)

import logging
import asyncio
from pathlib import Path

webhook_locks = {}
logger = logging.getLogger(__name__)
CUSTOM_SKILLS_DIR = Path(__file__).resolve().parent.parent / "my_custom_skills"

router = APIRouter()


def get_login_protocol(req: ConnectionRequest) -> str:
    return get_login_protocol_from_request(req)


def asset_matches_request(asset: dict, req: ConnectionRequest) -> bool:
    return asset_matches_connection_request(asset, req)


def _preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    try:
        return build_chat_attachment_preview(filename, content_type, content)
    except ChatAttachmentError as exc:
        raise_http_error(exc)


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

    try:
        run = start_session_chat_run(
            ssh_manager.active_sessions,
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
    except ChatSessionServiceError as exc:
        raise_http_error(exc)
    return StreamingResponse(run.subscribe(), media_type="text/event-stream")


@router.post("/chat/attachments/preview", response_model=ResponseModel)
async def preview_chat_attachment(file: UploadFile = File(...)):
    """Parse a small document for one-off chat context without ingesting it into the KB."""
    content = await file.read(CHAT_ATTACHMENT_MAX_SIZE + 1)
    attachment = _preview_attachment_content(
        file.filename or "",
        file.content_type or "application/octet-stream",
        content,
    )
    return ResponseModel(status="success", data={"attachment": attachment})


@router.post("/session/{session_id}/approve", response_model=ResponseModel)
async def approve_tool_call(session_id: str, req: ToolApprovalRequest):
    """【新功能】用户确认是否允许 AI 执行敏感指令"""
    from core.dispatcher import dispatcher
    from connections.ssh_manager import ssh_manager

    try:
        result = approve_session_tool_call(
            ssh_manager.active_sessions,
            dispatcher,
            session_id,
            req.tool_call_id,
            approved=req.approved,
            auto_approve_all=req.auto_approve_all,
            operator=req.operator or "user",
            note=req.note or "",
        )
    except SessionInteractionServiceError as exc:
        raise_http_error(exc)
    if result["include_approval"]:
        return ResponseModel(
            status="success",
            message=result["message"],
            data={"approval": result["approval"]},
        )
    return ResponseModel(status="success", message=result["message"])


@router.post("/session/{session_id}/interaction", response_model=ResponseModel)
async def respond_user_interaction(session_id: str, req: UserInteractionResponseRequest):
    """提交前台聊天中的文本、密码或选项交互响应。"""
    from core.dispatcher import dispatcher

    try:
        submit_user_interaction_response(
            dispatcher,
            session_id,
            req.request_id,
            value=req.value,
            label=req.label,
        )
    except SessionInteractionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="交互输入已提交。")


@router.get("/approvals", response_model=ResponseModel)
async def list_approval_requests(status: str | None = None, limit: int = 100):
    """查询高危工具调用审批队列。"""
    return ResponseModel(
        status="success",
        data={"approvals": list_approval_request_records(status=status, limit=limit)},
    )


@router.get("/approvals/{approval_id}", response_model=ResponseModel)
async def get_approval_request(approval_id: str):
    """查询单个审批请求。"""
    try:
        approval = get_approval_request_record(approval_id)
    except ApprovalRequestServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"approval": approval})


@router.post("/approvals/{approval_id}/decision", response_model=ResponseModel)
async def decide_approval_request(approval_id: str, req: ApprovalDecisionRequest):
    """审批或拒绝高危工具调用，并写入审计状态。"""
    from core.dispatcher import dispatcher

    try:
        approval = decide_approval_request_record(
            dispatcher,
            approval_id,
            approved=req.approved,
            operator=req.operator or "user",
            note=req.note or "",
        )
    except ApprovalRequestServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="审批已处理", data={"approval": approval})


@router.post("/approvals/{approval_id}/execute", response_model=ResponseModel)
async def execute_approval_request(approval_id: str):
    """执行已经批准且支持后续执行的审批请求。"""
    from core.dispatcher import dispatcher

    try:
        result = await execute_custom_skill_rollback_approval(
            approval_id,
            base_dir=CUSTOM_SKILLS_DIR,
            dispatcher=dispatcher,
        )
    except ApprovalExecutionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status=result.status,
        message=result.message,
        data={
            "approval": result.approval,
            "result": result.result,
        },
    )


@router.post("/session/{session_id}/stop", response_model=ResponseModel)
async def stop_chat_session(session_id: str):
    """【新功能】终止当前会话中正在生成的长流响应/执行任务"""
    from core.agent import cancel_flags

    request_session_stop(cancel_flags, session_id)
    return ResponseModel(status="success", message="已发送中止信号。")


def get_restored_connection_request(req: ConnectionRequest) -> tuple[ConnectionRequest, str | None]:
    """Restore masked asset secrets from persisted records before connection flows."""
    from core.memory import memory_db

    return restore_connection_request_secrets(req, memory_db)


@router.post("/connect/test", response_model=ResponseModel)
async def test_connection(req: ConnectionRequest):
    req, restored_password = get_restored_connection_request(req)
    result = await run_connection_test(req, restored_password)
    return ResponseModel(**result)


@router.post("/connect/inspect", response_model=ResponseModel)
async def inspect_connection(req: ConnectionInspectionRequest):
    """临时建立会话并执行只读巡检，默认巡检后自动断开。"""
    from core.session_inspector import inspect_session

    req, restored_password = get_restored_connection_request(req)
    result = await inspect_connection_session(
        req,
        ssh_manager,
        inspect_session,
        restored_password=restored_password,
    )
    return ResponseModel(**result)


@router.post("/connect", response_model=ResponseModel)
async def create_ssh_connection(req: ConnectionRequest):
    """建立与远程系统的会话 (支持 SSH长连接 或 虚拟凭据会话)"""
    req, restored_password = get_restored_connection_request(req)

    from core.memory import memory_db

    try:
        result = await create_connection_session(
            req,
            ssh_manager,
            memory_db,
            restored_password=restored_password,
            logger=logger,
        )
    except ConnectionSessionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**result)


@router.post("/execute", response_model=ResponseModel)
async def execute_remote_command(req: CommandRequest):
    """
    大模型使用的底层“Skill”核心：
    在已建立的 Session 中下发指令（如 uptime, ps aux）。
    """
    logger.info(f"API called: Executing legacy command on session {req.session_id}")

    from core.dispatcher import dispatcher

    try:
        data = await execute_legacy_command_record(
            ssh_manager.active_sessions,
            dispatcher,
            tool_registry,
            session_id=req.session_id,
            command=req.command,
        )
    except LegacyCommandServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(
        status="success",
        data=data,
    )


@router.post("/skills/scan", response_model=ResponseModel)
async def scan_skills():
    """【新功能】前端手动触发扫描本地磁盘目录，热加载新的技能"""
    from core.dispatcher import dispatcher

    result = scan_custom_skill_catalog(dispatcher)
    return ResponseModel(status="success", message=result["message"])


@router.get("/skills/registry", response_model=ResponseModel)
async def get_skill_registry():
    """【新功能】前端调用，获取所有已安装的技能卡带摘要以及外部市场待下载的卡带"""
    from core.dispatcher import dispatcher

    return ResponseModel(status="success", data=list_custom_skill_catalog(dispatcher))


@router.get("/skills/registry/{skill_id}", response_model=ResponseModel)
async def get_skill_detail(skill_id: str):
    """【新功能】前端调用，获取某个特定技能卡带的完整 Markdown 原文"""
    from core.dispatcher import dispatcher

    try:
        detail = get_custom_skill_detail_record(dispatcher, skill_id)
    except CustomSkillCatalogServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data=detail)


@router.post("/skills/create", response_model=ResponseModel)
async def create_skill(req: CreateSkillRequest):
    """【新功能】用户在页面上手动创建新的定制技能卡带"""
    try:
        from core.dispatcher import dispatcher

        result = create_custom_skill_record(
            CUSTOM_SKILLS_DIR,
            dispatcher,
            skill_id=req.skill_id,
            description=req.description,
            instructions=req.instructions,
            script_name=req.script_name,
            script_content=req.script_content,
            overwrite_existing=req.overwrite_existing,
        )
    except CustomSkillCreateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message=result["message"], data=result["data"])


@router.post("/skills/validate", response_model=ResponseModel)
async def validate_skill(req: SkillValidationRequest):
    """静态校验技能文件内容，不写文件、不执行脚本。"""
    result = validate_skill_candidate(req.skill_id, req.file_name, req.content)
    return ResponseModel(status="success", data=result)


@router.get("/skills/{skill_id}/versions", response_model=ResponseModel)
async def list_skill_versions(skill_id: str, file_name: str = "SKILL.md"):
    """列出 my_custom_skills 中某个技能文件的可回滚版本。"""
    try:
        versions = list_custom_skill_version_records(CUSTOM_SKILLS_DIR, skill_id, file_name)
    except CustomSkillVersionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"versions": versions})


@router.post("/skills/{skill_id}/rollback", response_model=ResponseModel)
async def rollback_skill_version(skill_id: str, req: SkillRollbackRequest):
    """将 my_custom_skills 中的技能文件回滚到指定备份版本。"""
    from core.dispatcher import dispatcher

    try:
        result = rollback_custom_skill_version_record(
            CUSTOM_SKILLS_DIR,
            dispatcher,
            skill_id=skill_id,
            file_name=req.file_name,
            version_id=req.version_id,
            approval_id=req.approval_id,
        )
    except CustomSkillRollbackServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status=result["status"],
        message=result["message"],
        data=result["data"],
    )


@router.post("/skills/migrate", response_model=ResponseModel)
async def migrate_skill(req: MigrateRequest):
    """将外部卡带拷贝到专属的 my_custom_skills 目录"""
    try:
        from core.dispatcher import dispatcher

        result = migrate_custom_skill_record(
            CUSTOM_SKILLS_DIR,
            dispatcher,
            source_path=req.source_path,
            target_dir_name=req.target_dir_name,
        )
    except CustomSkillMigrationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message=result["message"])


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
    return ResponseModel(status="success", data=build_llm_config_payload())



@router.get("/config/agent-runtime", response_model=ResponseModel)
async def get_agent_runtime_config_endpoint():
    return ResponseModel(status="success", data={"config": get_agent_runtime_config_record()})


@router.post("/config/agent-runtime", response_model=ResponseModel)
async def update_agent_runtime_config_endpoint(req: AgentRuntimeConfigRequest):
    try:
        config = save_agent_runtime_config_record(req.chat_max_steps, req.headless_max_steps)
    except AppConfigServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"config": config}, message="Agent 执行保护配置已保存")


@router.get("/config/embedding")
async def get_embedding_config_endpoint():
    return {"status": "success", "data": get_embedding_config_record()}


@router.post("/config/embedding", response_model=ResponseModel)
async def update_embedding_config_endpoint(req: EmbeddingConfigRequest):
    try:
        save_embedding_config_record(req.model, req.dim)
        return ResponseModel(
            status="success",
            message=f"Embedding 配置已更新: model={req.model}, dim={req.dim}",
        )
    except AppConfigServiceError as exc:
        raise_http_error(exc)


@router.get("/config/notifications", response_model=ResponseModel)
async def get_notification_config():
    """【新功能】获取当前的告警通道配置"""
    return ResponseModel(status="success", data=build_notification_config())


@router.post("/config/notifications", response_model=ResponseModel)
async def update_notification_config(req: NotificationConfigRequest):
    """【新功能】前端动态配置企业微信/钉钉告警机器人 Webhook 及邮件"""
    try:
        from core.app_config_service import update_env_file_values

        save_notification_config_record(req.model_dump(), persist=update_env_file_values)
    except Exception as e:
        logger.error(f"Failed to save .env file: {e}")

    logger.info("Notification Webhooks updated.")
    return ResponseModel(status="success", message="告警通道配置已保存并生效")


@router.post("/config/notifications/test", response_model=ResponseModel)
async def test_notification_channel(req: TestNotificationRequest):
    """【新功能】测试通知渠道"""
    try:
        message = send_notification_channel_test(req.channel)
        return ResponseModel(status="success", message=message)
    except NotificationTestError as exc:
        raise_http_error(exc)
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
        raise_http_error(exc)
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
        raise_http_error(exc)

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
        raise_http_error(exc)

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
        messages = list_session_history_messages(memory_db, session_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"messages": messages})


@router.delete("/session/{session_id}/history", response_model=ResponseModel)
async def delete_session_history(session_id: str):
    """【新功能】清空会话的聊天记录"""
    from core.memory import memory_db

    try:
        clear_session_history_messages(memory_db, session_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="会话记录已清空")


@router.patch("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def update_session_history_message(
    session_id: str,
    message_id: int,
    req: SessionMessageUpdateRequest,
):
    """修改单条用户可见会话消息。"""
    from core.memory import memory_db

    try:
        message = update_session_history_message_record(
            memory_db,
            session_id,
            message_id,
            req.content,
        )
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"message": message}, message="消息已更新")


@router.delete("/session/{session_id}/history/{message_id}", response_model=ResponseModel)
async def delete_session_history_message(session_id: str, message_id: int):
    """删除单条用户可见会话消息。"""
    from core.memory import memory_db

    try:
        delete_session_history_message_record(memory_db, session_id, message_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="消息已删除")


@router.put("/session/{session_id}/skills", response_model=ResponseModel)
async def update_session_skills(session_id: str, req: SkillsUpdateRequest):
    """【新功能】动态修改挂载技能包：在不中断会话的情况下，挂载或卸载 AI 技能"""
    try:
        set_session_skills(ssh_manager.active_sessions, session_id, req.active_skills)
    except SessionRuntimeError as exc:
        raise_http_error(exc)
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
        raise_http_error(exc)
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


@router.get("/tools/catalog", response_model=ResponseModel)
async def get_tool_catalog():
    """返回平台内置工具目录。仅包含工具元数据，不包含任何资产凭据。"""
    return ResponseModel(status="success", data=tool_registry.catalog())


@router.get("/session/{session_id}/tools", response_model=ResponseModel)
async def get_session_tools(session_id: str):
    """返回指定会话当前会暴露给模型的工具集。"""
    try:
        payload = build_session_tools_payload_for_session(
            ssh_manager.active_sessions,
            tool_registry,
            session_id,
        )
    except SessionToolContextError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status="success",
        data=payload,
    )


@router.get("/session/{session_id}/commands", response_model=ResponseModel)
async def get_session_commands(session_id: str):
    """返回当前会话可用 Slash Commands；由后端根据资产协议生成 prompt。"""
    from core.memory import memory_db

    try:
        tools_payload = build_session_tools_payload_for_session(
            ssh_manager.active_sessions,
            tool_registry,
            session_id,
        )
    except SessionToolContextError as exc:
        raise_http_error(exc)
    custom_commands = await asyncio.to_thread(list_custom_slash_commands_data, memory_db)
    return ResponseModel(
        status="success",
        data=build_session_commands_response(tools_payload, custom_commands),
    )


@router.get("/commands/custom", response_model=ResponseModel)
async def list_custom_slash_commands():
    """列出用户自定义快捷命令。"""
    from core.memory import memory_db

    commands = await asyncio.to_thread(list_custom_slash_commands_data, memory_db)
    return ResponseModel(status="success", data={"commands": commands})


@router.post("/commands/custom", response_model=ResponseModel)
async def create_custom_slash_command(req: SlashCommandPayload):
    """创建用户自定义快捷命令。"""
    from core.memory import memory_db

    command = await asyncio.to_thread(
        save_custom_slash_command,
        memory_db,
        req.model_dump(),
    )
    return ResponseModel(status="success", message="快捷命令已保存", data={"command": command})


@router.put("/commands/custom/{command_id}", response_model=ResponseModel)
async def update_custom_slash_command(command_id: str, req: SlashCommandPayload):
    """更新用户自定义快捷命令。"""
    from core.memory import memory_db

    command = await asyncio.to_thread(
        save_custom_slash_command,
        memory_db,
        req.model_dump(),
        command_id,
    )
    return ResponseModel(status="success", message="快捷命令已更新", data={"command": command})


@router.delete("/commands/custom/{command_id}", response_model=ResponseModel)
async def delete_custom_slash_command(command_id: str):
    """删除用户自定义快捷命令。"""
    from core.memory import memory_db

    try:
        await asyncio.to_thread(remove_custom_slash_command, memory_db, command_id)
    except SessionCommandError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="快捷命令已删除")


@router.get("/inspection-templates", response_model=ResponseModel)
async def list_inspection_templates():
    """列出内置与自定义巡检模板。"""
    return ResponseModel(
        status="success",
        data={"templates": list_inspection_template_records()},
    )


@router.post("/inspection-templates", response_model=ResponseModel)
async def create_inspection_template(req: InspectionTemplatePayload):
    """创建巡检模板；模板必须通过只读安全校验。"""
    try:
        template = save_inspection_template_record(req.model_dump())
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检模板已保存", data={"template": template})


@router.put("/inspection-templates/{template_id}", response_model=ResponseModel)
async def update_inspection_template(template_id: str, req: InspectionTemplatePayload):
    """更新巡检模板；路径 ID 优先，避免请求体误改主键。"""
    try:
        template = save_inspection_template_record(req.model_dump(), template_id)
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检模板已更新", data={"template": template})


@router.delete("/inspection-templates/{template_id}", response_model=ResponseModel)
async def delete_inspection_template(template_id: str):
    """删除巡检模板。"""
    try:
        remove_inspection_template_record(template_id)
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检模板已删除")


@router.post("/session/{session_id}/inspect", response_model=ResponseModel)
async def inspect_active_session(session_id: str):
    """对已建立的会话执行只读巡检。"""
    from core.session_inspector import inspect_session

    report = await inspect_session(session_id)
    return ResponseModel(**build_inspection_response_payload(report))


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


@router.post("/session/{session_id}/webhook/send", response_model=ResponseModel)
async def send_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """将会话画像、摘要或完整 Markdown 发送到指定 Webhook。"""
    from core.memory import memory_db

    try:
        payload = await send_session_webhook_delivery(
            memory_db,
            ssh_manager.active_sessions,
            session_id=session_id,
            **session_webhook_delivery_kwargs(req),
        )
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status="success",
        message="Webhook 已发送",
        data=payload,
    )


@router.post("/session/{session_id}/webhook/preview", response_model=ResponseModel)
async def preview_session_webhook(session_id: str, req: SessionWebhookSendRequest):
    """发送前预览会话 Webhook 目标和载荷，不实际发出请求。"""
    from core.memory import memory_db

    try:
        payload = await preview_session_webhook_delivery(
            memory_db,
            ssh_manager.active_sessions,
            session_id=session_id,
            **session_webhook_delivery_kwargs(req),
        )
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data=payload)


@router.get("/session/{session_id}/webhook/history", response_model=ResponseModel)
async def list_session_webhook_history(session_id: str, limit: int = 10):
    """查看当前会话最近 Webhook 发送历史。"""
    from core.memory import memory_db

    try:
        deliveries = await list_session_webhook_delivery_records(memory_db, session_id, limit)
    except SessionWebhookServiceError as exc:
        raise_http_error(exc)
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

    assets = await asyncio.to_thread(list_saved_asset_records, memory_db)
    return ResponseModel(status="success", data={"assets": assets})


@router.post("/assets", response_model=ResponseModel)
async def create_asset(req: AssetPayload):
    """创建或按 host+资产类型+协议更新资产；密码和敏感 extra_args 会加密保存。"""
    from core.memory import memory_db

    await asyncio.to_thread(save_asset_record, memory_db, req.model_dump())
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

    try:
        asset = await asyncio.to_thread(get_saved_asset_record, memory_db, asset_id)
    except AssetServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"asset": asset})


@router.put("/assets/{asset_id}", response_model=ResponseModel)
async def update_asset(asset_id: int, req: AssetPayload):
    """按资产 ID 修改资产；传入 ******** 会保留原密码/密钥。"""
    from core.memory import memory_db

    try:
        asset = await asyncio.to_thread(update_saved_asset_record, memory_db, asset_id, req.model_dump())
    except AssetServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status="success",
        message="资产已更新",
        data={"asset": asset},
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

    await asyncio.to_thread(remove_saved_asset_record, memory_db, asset_id)
    return ResponseModel(status="success", message="资产已成功移除金库。")


@router.get("/dashboard/overview", response_model=ResponseModel)
async def get_dashboard_overview():
    """大屏总览接口：资产、在线会话、协议、分类和基础风险计数。"""
    from core.memory import memory_db

    data = await asyncio.to_thread(build_dashboard_overview_payload, memory_db, ssh_manager.active_sessions)
    return ResponseModel(status="success", data=data)


@router.get("/dashboard/toolsets", response_model=ResponseModel)
async def get_dashboard_toolsets():
    """大屏/配置页工具集接口：展示平台工具覆盖度。"""
    catalog = tool_registry.catalog()
    return ResponseModel(status="success", data=catalog)


@router.get("/dashboard/alerts/trend", response_model=ResponseModel)
async def get_dashboard_alert_trend():
    """大屏告警趋势接口，按日期聚合告警数量和严重级别。"""
    data = await asyncio.to_thread(build_dashboard_alert_trend_payload)
    return ResponseModel(status="success", data=data)


@router.get("/dashboard/risk-ranking", response_model=ResponseModel)
async def get_dashboard_risk_ranking():
    """大屏风险排行接口，当前按告警数量和严重度聚合主机风险。"""
    data = await asyncio.to_thread(build_dashboard_risk_ranking_payload)
    return ResponseModel(status="success", data=data)


@router.get("/dashboard/inspection-runs/trend", response_model=ResponseModel)
async def get_dashboard_inspection_run_trend():
    data = await asyncio.to_thread(build_dashboard_inspection_run_trend_payload)
    return ResponseModel(status="success", data=data)


@router.get("/verification/protocols", response_model=ResponseModel)
async def get_protocol_verification_overview():
    """返回全量资产协议验证矩阵概览，不包含任何敏感凭据。"""
    from core.memory import memory_db

    data = await asyncio.to_thread(build_protocol_verification_overview, memory_db)
    return ResponseModel(status="success", data=data)


@router.get("/assets/{asset_id}/verification", response_model=ResponseModel)
async def get_asset_verification_matrix(asset_id: int):
    """返回单资产协议验证矩阵，不包含任何敏感凭据。"""
    from core.memory import memory_db

    try:
        matrix = await asyncio.to_thread(build_protocol_verification_matrix, memory_db, asset_id)
    except ProtocolVerificationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"matrix": matrix})


@router.post("/assets/{asset_id}/verify", response_model=ResponseModel)
async def verify_asset(asset_id: int):
    """执行单资产只读端到端验证，并持久化验证历史。"""
    from core.memory import memory_db

    try:
        run = await run_protocol_verification_for_asset(memory_db, asset_id)
    except ProtocolVerificationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"run": run})


@router.get("/assets/{asset_id}/verification/runs", response_model=ResponseModel)
async def list_asset_verification_runs(asset_id: int, limit: int = 20):
    """查询单资产验证历史。"""
    runs = await asyncio.to_thread(list_protocol_verification_run_records, asset_id, limit)
    return ResponseModel(status="success", data={"runs": runs})


@router.get("/alerts", response_model=ResponseModel)
async def list_alert_events(status: str | None = None, severity: str | None = None, host: str | None = None, limit: int = 200):
    """查询告警事件。"""
    return ResponseModel(
        status="success",
        data={"alerts": list_alert_event_records(status=status, severity=severity, host=host, limit=limit)},
    )


@router.get("/alerts/{alert_id}", response_model=ResponseModel)
async def get_alert_event(alert_id: str):
    """查询单个告警事件。"""
    try:
        alert = get_alert_event_record(alert_id)
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"alert": alert})


@router.patch("/alerts/{alert_id}", response_model=ResponseModel)
async def update_alert_event(alert_id: str, req: AlertEventUpdateRequest):
    """更新告警状态、处理人或备注。"""
    try:
        alert = update_alert_event_record(
            alert_id,
            status=req.status,
            assignee=req.assignee,
            note=req.note,
        )
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"alert": alert})


# ----------------- OpenClaw / ManageEngine Webhook 闭环设计 -----------------
from fastapi import Request

from fastapi import UploadFile, File


@router.post("/knowledge/upload", response_model=ResponseModel)
async def upload_knowledge_document(file: UploadFile = File(...)):
    """【新功能】上传运维文档并注入 LanceDB 知识库"""
    from core.rag import kb_manager

    try:
        message = await ingest_knowledge_document(kb_manager, file)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message=message)


@router.get("/knowledge/list", response_model=ResponseModel)
async def list_knowledge_documents():
    """【新功能】列出已注入知识库的文档列表"""
    from core.rag import kb_manager

    try:
        files = await list_knowledge_document_records(kb_manager)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"files": files})


@router.delete("/knowledge/{filename}", response_model=ResponseModel)
async def delete_knowledge_document(filename: str):
    """【新功能】从知识库中删除某个文档"""
    from core.rag import kb_manager

    try:
        message = await remove_knowledge_document_record(kb_manager, filename)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message=message)


@router.post("/webhook/alert", response_model=ResponseModel)
async def receive_webhook_alert(request: Request):
    """【AIOps 高级特性】接收外部告警 (Prometheus / ManageEngine) 并推入相关 AI 会话"""
    payload = await read_alert_webhook_payload(request.json)

    from core.memory import memory_db
    from core.dispatcher import dispatcher
    from core.heartbeat import run_single_heartbeat

    result = await handle_alert_webhook(
        payload,
        ssh_manager.active_sessions,
        webhook_locks,
        memory_db,
        dispatcher,
        run_single_heartbeat,
    )

    return ResponseModel(
        status="success",
        message=result["message"],
        data=result["data"],
    )


# ----------------- OpenClaw 自动化巡检 (Cron Jobs) -----------------
@router.post("/cron/add", response_model=ResponseModel)
async def add_cron_job(req: CronAddRequest):
    """【新功能】添加大模型定时巡检任务 (类似 openclaw cron add)"""
    try:
        payload = create_inspection_job_record(req.model_dump())
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        status="success",
        message=f"已成功添加定时巡检计划: {payload['job_id']}",
        data=payload,
    )


@router.get("/cron/list", response_model=ResponseModel)
async def list_cron_jobs():
    """【新功能】查看所有的定时巡检计划"""
    jobs = await asyncio.to_thread(list_inspection_job_records)
    return ResponseModel(status="success", data={"jobs": jobs})


@router.delete("/cron/{job_id}", response_model=ResponseModel)
async def delete_cron_job(job_id: str):
    """【新功能】删除某个定时巡检计划"""
    try:
        await asyncio.to_thread(remove_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message=f"巡检计划 {job_id} 已取消。")


@router.put("/cron/{job_id}", response_model=ResponseModel)
async def update_cron_job(job_id: str, req: CronAddRequest):
    try:
        job = await asyncio.to_thread(update_inspection_job_record, job_id, req.model_dump())
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检计划已更新", data={"job": job})


@router.post("/cron/{job_id}/pause", response_model=ResponseModel)
async def pause_cron_job(job_id: str):
    try:
        job = await asyncio.to_thread(pause_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检计划已暂停", data={"job": job})


@router.post("/cron/{job_id}/resume", response_model=ResponseModel)
async def resume_cron_job(job_id: str):
    try:
        job = await asyncio.to_thread(resume_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检计划已恢复", data={"job": job})


@router.post("/cron/{job_id}/run", response_model=ResponseModel)
async def run_cron_job_now(job_id: str):
    try:
        result = await run_inspection_job_record_now(job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="巡检计划已手动触发", data={"result": result})


@router.get("/cron/{job_id}/runs", response_model=ResponseModel)
async def list_cron_job_runs(job_id: str, limit: int = 50, asset_id: int | None = None):
    return ResponseModel(
        status="success",
        data={"runs": list_inspection_run_records(job_id=job_id, limit=limit, asset_id=asset_id)},
    )


@router.get("/inspection-runs", response_model=ResponseModel)
async def list_inspection_runs(job_id: str | None = None, asset_id: int | None = None, limit: int = 50):
    return ResponseModel(
        status="success",
        data={"runs": list_inspection_run_records(job_id=job_id, asset_id=asset_id, limit=limit)},
    )


@router.get("/cron/runs/summary", response_model=ResponseModel)
async def get_cron_run_summary():
    return ResponseModel(status="success", data={"summary": inspection_run_summary()})


@router.get("/cron/runs/{run_id}", response_model=ResponseModel)
async def get_cron_job_run(run_id: str):
    try:
        run = get_inspection_run_record(run_id)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"run": run})


@router.get("/inspection-runs/{run_id}/report", response_model=ResponseModel)
async def get_inspection_run_report(run_id: str):
    try:
        report = get_inspection_run_report_record(run_id)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"report": report})


@router.get("/inspection-runs/{run_id}/export", response_model=ResponseModel)
async def export_inspection_run_report(run_id: str, format: str = "markdown"):
    try:
        payload = export_inspection_run_report_content(run_id, format)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data=payload)


# ----------------- 系统状态与高级功能 -----------------


@router.get("/hydrate/status", response_model=ResponseModel)
async def get_hydrate_status():
    """【新功能】获取启动时资产重连的进度，前端可轮询此接口展示启动状态"""
    from main import hydrate_status

    return ResponseModel(status="success", data=hydrate_status)


@router.post("/assets/batch_import", response_model=ResponseModel)
async def batch_import_assets(items: list[BatchAssetImportItem]):
    """【#25 新功能】批量导入资产到金库（通讯录），支持 JSON 数组格式"""
    from core.memory import memory_db

    try:
        result = await asyncio.to_thread(
            batch_import_asset_records,
            memory_db,
            [item.model_dump() for item in items],
        )
    except AssetServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(status="success", message=f"成功导入 {result['imported']}/{result['total']} 条资产。")


@router.get("/session/{session_id}/export", response_model=ResponseModel)
async def export_session_history(session_id: str):
    """【#22 新功能】服务端导出会话历史为 Markdown 格式"""
    from core.memory import memory_db

    try:
        markdown = export_session_history_markdown_record(memory_db, ssh_manager.active_sessions, session_id)
    except SessionHistoryServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", data={"markdown": markdown})


@router.get("/config/providers", response_model=ResponseModel)
async def get_providers_endpoint():
    providers = await asyncio.to_thread(list_provider_config_records)
    return ResponseModel(status="success", data={"providers": providers})

@router.post("/config/providers", response_model=ResponseModel)
async def update_providers_endpoint(req: list[ProviderConfig]):
    try:
        await asyncio.to_thread(save_provider_config_records, [p.model_dump() for p in req])
    except ProviderConfigServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="供应商配置已保存")


@router.get("/config/safety-policy", response_model=ResponseModel)
async def get_safety_policy_endpoint():
    return ResponseModel(status="success", data={"policy": get_safety_policy_record()})


@router.post("/config/safety-policy", response_model=ResponseModel)
async def update_safety_policy_endpoint(req: SafetyPolicyUpdateRequest):
    try:
        policy = save_safety_policy_record(req.policy)
    except SafetyPolicyServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(status="success", message="安全策略已保存", data={"policy": policy})


@router.post("/config/safety-policy/test", response_model=ResponseModel)
async def test_safety_policy_endpoint(req: SafetyPolicyTestRequest):
    result = explain_safety_policy_test(req)
    return ResponseModel(status="success", data={"result": result})

