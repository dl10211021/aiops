from __future__ import annotations

from typing import Any

from api.schema_models.sessions import (
    HeartbeatUpdateRequest,
    PermissionUpdateRequest,
    SessionGroupUpdateRequest,
    SessionMetadataUpdateRequest,
    SessionProfileGenerateRequest,
    SessionWebhookSendRequest,
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


def session_metadata_update_kwargs(req: SessionMetadataUpdateRequest) -> dict[str, Any]:
    return {
        "remark": req.remark,
        "group_name": req.group_name,
        "tags": req.tags,
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


def session_history_export_response_kwargs(markdown: str) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"markdown": markdown},
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


def session_metadata_response_kwargs(
    session_id: str,
    info: dict[str, Any],
    group_name: str,
) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "会话信息已更新",
        "data": {
            "session_id": session_id,
            "remark": info.get("remark") or "",
            "tags": info["tags"],
            "group_name": group_name,
        },
    }
