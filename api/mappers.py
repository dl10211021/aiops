from __future__ import annotations

from typing import Any

from api.schemas import (
    AlertEventUpdateRequest,
    AssetPayload,
    BatchAssetImportItem,
    ChatRequest,
    CreateSkillRequest,
    CronAddRequest,
    HeartbeatUpdateRequest,
    InspectionTemplatePayload,
    MigrateRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionProfileGenerateRequest,
    SessionWebhookSendRequest,
    SkillRollbackRequest,
)


def chat_stream_agent_kwargs(req: ChatRequest) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "user_message": req.message,
        "user_display_message": req.display_message,
        "model_name": req.model_name,
        "thinking_mode": req.thinking_mode or "off",
        "user_attachments": req.attachments,
    }


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


def custom_skill_create_kwargs(req: CreateSkillRequest) -> dict[str, Any]:
    return {
        "skill_id": req.skill_id,
        "description": req.description,
        "instructions": req.instructions,
        "script_name": req.script_name,
        "script_content": req.script_content,
        "overwrite_existing": req.overwrite_existing,
    }


def custom_skill_rollback_kwargs(req: SkillRollbackRequest) -> dict[str, Any]:
    return {
        "file_name": req.file_name,
        "version_id": req.version_id,
        "approval_id": req.approval_id,
    }


def custom_skill_migration_kwargs(req: MigrateRequest) -> dict[str, Any]:
    return {
        "source_path": req.source_path,
        "target_dir_name": req.target_dir_name,
    }


def inspection_template_save_payload(req: InspectionTemplatePayload) -> dict[str, Any]:
    return req.model_dump()


def inspection_template_list_response_kwargs(templates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"templates": templates},
    }


def inspection_template_saved_response_kwargs(
    template: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "data": {"template": template},
    }


def inspection_template_deleted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "巡检模板已删除",
    }


def cron_job_payload(req: CronAddRequest) -> dict[str, Any]:
    return req.model_dump()


def cron_job_created_response_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"已成功添加定时巡检计划: {payload['job_id']}",
        "data": payload,
    }


def cron_jobs_response_kwargs(jobs: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"jobs": jobs},
    }


def cron_job_deleted_response_kwargs(job_id: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"巡检计划 {job_id} 已取消。",
    }


def cron_job_response_kwargs(job: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "data": {"job": job},
    }


def cron_job_run_trigger_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "巡检计划已手动触发",
        "data": {"result": result},
    }


def inspection_runs_response_kwargs(runs: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"runs": runs},
    }


def inspection_run_summary_response_kwargs(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"summary": summary},
    }


def inspection_run_response_kwargs(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"run": run},
    }


def inspection_run_report_response_kwargs(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"report": report},
    }


def inspection_run_export_response_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": payload,
    }


def dashboard_response_kwargs(data: Any) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def asset_payload(req: AssetPayload) -> dict[str, Any]:
    return req.model_dump()


def batch_asset_import_payload(items: list[BatchAssetImportItem]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]


def saved_assets_response_kwargs(assets: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"assets": assets},
    }


def asset_saved_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已保存",
    }


def asset_types_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def asset_response_kwargs(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"asset": asset},
    }


def asset_updated_response_kwargs(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已更新",
        "data": {"asset": asset},
    }


def asset_deleted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已成功移除金库。",
    }


def batch_asset_import_response_kwargs(result: dict[str, int]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"成功导入 {result['imported']}/{result['total']} 条资产。",
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


def alert_event_list_query_kwargs(
    status: str | None,
    severity: str | None,
    host: str | None,
    limit: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "severity": severity,
        "host": host,
        "limit": limit,
    }


def alert_event_update_kwargs(req: AlertEventUpdateRequest) -> dict[str, Any]:
    return {
        "status": req.status,
        "assignee": req.assignee,
        "note": req.note,
    }


def alert_events_response_kwargs(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"alerts": alerts},
    }


def alert_event_response_kwargs(alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"alert": alert},
    }


def alert_webhook_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": result["message"],
        "data": result["data"],
    }


def knowledge_document_uploaded_response_kwargs(message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }


def knowledge_documents_response_kwargs(files: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"files": files},
    }


def knowledge_document_deleted_response_kwargs(message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }


def session_poll_response_kwargs(pending: list[Any] | None) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"messages": pending or []},
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
