from __future__ import annotations

from typing import Any

from api.schemas import (
    ChatRequest,
    CreateSkillRequest,
    HeartbeatUpdateRequest,
    MigrateRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
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


def session_poll_response_kwargs(pending: list[Any] | None) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"messages": pending or []},
    }


def session_group_response_kwargs(session_id: str, info: dict[str, Any], group_name: str) -> dict[str, Any]:
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
