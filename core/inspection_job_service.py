from __future__ import annotations

from typing import Any

from core.cron_manager import CronManager


class InspectionJobServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _cron_job_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "cron_expr": payload.get("cron_expr"),
        "host": payload.get("host"),
        "username": payload.get("username"),
        "agent_profile": payload.get("agent_profile"),
        "message": payload.get("message"),
        "password": payload.get("password"),
        "private_key_path": payload.get("private_key_path"),
        "asset_id": payload.get("asset_id"),
        "target_scope": payload.get("target_scope"),
        "scope_value": payload.get("scope_value"),
        "template_id": payload.get("template_id"),
        "notification_channel": payload.get("notification_channel"),
        "retry_count": payload.get("retry_count"),
        "active_skills": payload.get("active_skills") or [],
    }


def create_inspection_job_record(
    payload: dict[str, Any],
    manager=CronManager,
) -> dict[str, Any]:
    try:
        job_id = manager.add_inspection_job(**_cron_job_kwargs(payload))
        return {"job_id": job_id, "job": manager.get_job(job_id)}
    except Exception as exc:
        raise InspectionJobServiceError(400, str(exc)) from exc


def list_inspection_job_records(manager=CronManager) -> list[dict[str, Any]]:
    return manager.get_all_jobs()


def remove_inspection_job_record(job_id: str, manager=CronManager) -> None:
    try:
        manager.remove_job(job_id)
    except Exception as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc


def update_inspection_job_record(
    job_id: str,
    payload: dict[str, Any],
    manager=CronManager,
) -> dict[str, Any]:
    try:
        return manager.update_job(job_id, **_cron_job_kwargs(payload))
    except KeyError as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc
    except Exception as exc:
        raise InspectionJobServiceError(400, str(exc)) from exc


def pause_inspection_job_record(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return manager.pause_job(job_id)
    except Exception as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc


def resume_inspection_job_record(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return manager.resume_job(job_id)
    except Exception as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc


async def run_inspection_job_record_now(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return await manager.run_job_now(job_id)
    except KeyError as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc
