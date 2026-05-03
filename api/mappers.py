from __future__ import annotations

from typing import Any

from api.schemas import (
    HeartbeatUpdateRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionProfileGenerateRequest,
    SessionWebhookSendRequest,
)
from api.response_mappers.chat import (
    chat_attachment_preview_response_kwargs,
    chat_stop_response_kwargs,
    chat_stream_agent_kwargs,
)
from api.response_mappers.skills import (
    custom_skill_create_kwargs,
    custom_skill_migration_kwargs,
    custom_skill_rollback_kwargs,
    skill_created_response_kwargs,
    skill_detail_response_kwargs,
    skill_migration_response_kwargs,
    skill_registry_response_kwargs,
    skill_rollback_response_kwargs,
    skill_scan_response_kwargs,
    skill_validation_response_kwargs,
    skill_versions_response_kwargs,
)
from api.response_mappers.assets import (
    asset_deleted_response_kwargs,
    asset_normalization_applied_response_kwargs,
    asset_normalization_preview_response_kwargs,
    asset_payload,
    asset_response_kwargs,
    asset_saved_response_kwargs,
    asset_types_response_kwargs,
    asset_updated_response_kwargs,
    batch_asset_import_payload,
    batch_asset_import_response_kwargs,
    saved_assets_response_kwargs,
)
from api.response_mappers.inspection import (
    cron_job_created_response_kwargs,
    cron_job_deleted_response_kwargs,
    cron_job_payload,
    cron_job_response_kwargs,
    cron_job_run_trigger_response_kwargs,
    cron_jobs_response_kwargs,
    inspection_run_export_response_kwargs,
    inspection_run_report_response_kwargs,
    inspection_run_response_kwargs,
    inspection_run_summary_response_kwargs,
    inspection_runs_response_kwargs,
    inspection_template_deleted_response_kwargs,
    inspection_template_list_response_kwargs,
    inspection_template_save_payload,
    inspection_template_saved_response_kwargs,
)
from api.response_mappers.system import (
    dashboard_response_kwargs,
    system_info_response_kwargs,
)
from api.response_mappers.notifications import (
    notification_channel_test_response_kwargs,
    notification_config_response_kwargs,
    notification_config_saved_response_kwargs,
)
from api.response_mappers.knowledge import (
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
)
from api.response_mappers.alerts import (
    alert_event_list_query_kwargs,
    alert_event_response_kwargs,
    alert_event_update_kwargs,
    alert_events_response_kwargs,
    alert_webhook_response_kwargs,
)


def session_webhook_delivery_kwargs(req: SessionWebhookSendRequest) -> dict[str, Any]:
    return {
        "webhook_url": req.webhook_url,
        "payload_type": req.payload_type,
        "channel": req.channel,
        "title": req.title,
        "model_name": req.model_name,
        "allow_private_targets": req.allow_private_targets,
    }


def session_permission_update_kwargs(req: PermissionUpdateRequest) -> dict[str, Any]:
    return {"allow_modifications": req.allow_modifications}


def session_heartbeat_update_kwargs(req: HeartbeatUpdateRequest) -> dict[str, Any]:
    return {
        "heartbeat_enabled": req.heartbeat_enabled,
        "master_interval": req.master_interval,
    }


def session_group_update_kwargs(req: SessionGroupUpdateRequest) -> dict[str, Any]:
    return {"group_name": req.group_name}


def models_response_kwargs(models: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"models": models},
    }


def llm_config_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": config,
    }


def agent_runtime_config_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"config": config},
    }


def agent_runtime_config_saved_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"config": config},
        "message": "Agent 执行保护配置已保存",
    }


def embedding_config_saved_response_kwargs(model: str, dim: int) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"Embedding 配置已更新: model={model}, dim={dim}",
    }


def providers_response_kwargs(providers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"providers": providers},
    }


def providers_saved_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "供应商配置已保存",
    }


def safety_policy_response_kwargs(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"policy": policy},
    }


def safety_policy_saved_response_kwargs(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "安全策略已保存",
        "data": {"policy": policy},
    }


def safety_policy_test_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"result": result},
    }


def session_profile_generate_kwargs(req: SessionProfileGenerateRequest) -> dict[str, Any]:
    return {
        "model_name": req.model_name,
        "include_inspection": req.include_inspection,
    }


def session_profile_response_kwargs(profile: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"profile": profile},
    }


def session_profile_generated_response_kwargs(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产画像已生成",
        "data": {"profile": profile},
    }


def protocol_verification_overview_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def asset_verification_matrix_response_kwargs(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"matrix": matrix},
    }


def asset_verification_run_response_kwargs(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"run": run},
    }


def asset_verification_runs_response_kwargs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"runs": runs},
    }


def session_poll_response_kwargs(pending: list[Any] | None) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"messages": pending or []},
    }


def all_sessions_poll_response_kwargs(updates: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"updates": updates},
    }


def session_permission_updated_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "权限已实时更新",
    }


def session_heartbeat_updated_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "心跳巡检状态已更新",
    }


def session_history_response_kwargs(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"messages": messages},
    }


def session_history_cleared_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "会话记录已清空",
    }


def session_history_message_updated_response_kwargs(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"message": message},
        "message": "消息已更新",
    }


def session_history_message_deleted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "消息已删除",
    }


def session_skills_updated_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "挂载技能已实时更新",
    }


def active_sessions_response_kwargs(sessions: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"sessions": sessions},
    }


def tool_catalog_response_kwargs(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": catalog,
    }


def session_commands_response_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": payload,
    }


def custom_slash_commands_response_kwargs(commands: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"commands": commands},
    }


def custom_slash_command_saved_response_kwargs(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "快捷命令已保存",
        "data": {"command": command},
    }


def custom_slash_command_updated_response_kwargs(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "快捷命令已更新",
        "data": {"command": command},
    }


def custom_slash_command_deleted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "快捷命令已删除",
    }


def session_webhook_sent_response_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "Webhook 已发送",
        "data": payload,
    }


def session_webhook_preview_response_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": payload,
    }


def session_webhook_history_response_kwargs(deliveries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"deliveries": deliveries},
    }


def session_closed_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "Connection closed safely",
    }


def session_history_export_response_kwargs(markdown: str) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"markdown": markdown},
    }


def user_interaction_submitted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "交互输入已提交。",
    }


def approval_requests_response_kwargs(approvals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"approvals": approvals},
    }


def approval_request_response_kwargs(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"approval": approval},
    }


def approval_decision_response_kwargs(approval: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "审批已处理",
        "data": {"approval": approval},
    }


def approval_execution_response_kwargs(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "message": result.message,
        "data": {
            "approval": result.approval,
            "result": result.result,
        },
    }


def legacy_command_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def session_group_response_kwargs(
    session_id: str,
    info: dict[str, Any],
    group_name: str,
) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "会话分组已更新",
        "data": {
            "session_id": session_id,
            "tags": info["tags"],
            "group_name": group_name,
        },
    }


def tool_approval_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    response = {
        "status": "success",
        "message": result["message"],
    }
    if result["include_approval"]:
        response["data"] = {"approval": result["approval"]}
    return response
