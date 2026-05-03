from __future__ import annotations

from typing import Any

from api.schemas import CreateSkillRequest, MigrateRequest, SkillRollbackRequest


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


def skill_scan_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": result["message"],
    }


def skill_registry_response_kwargs(registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": registry,
    }


def skill_detail_response_kwargs(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": detail,
    }


def skill_created_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": result["message"],
        "data": result["data"],
    }


def skill_validation_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": result,
    }


def skill_versions_response_kwargs(versions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"versions": versions},
    }


def skill_rollback_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result["status"],
        "message": result["message"],
        "data": result["data"],
    }


def skill_migration_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": result["message"],
    }
