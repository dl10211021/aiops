from __future__ import annotations

from typing import Any

from core.cron_manager import CronManager


class InspectionJobServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _job_matches_query(job: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    needle = query.strip().lower()
    return any(
        needle in str(job.get(field) or "").lower()
        for field in (
            "id",
            "host",
            "target_host",
            "username",
            "message",
            "scope_value",
            "template_id",
            "asset_id",
            "inspection_cycle",
            "inspection_depth",
        )
    )


def _job_matches_status(job: dict[str, Any], status: str) -> bool:
    if status in {"", "all"}:
        return True
    if status == "scheduled":
        return job.get("status") != "paused"
    if status == "paused":
        return job.get("status") == "paused"
    run_state = job.get("run_state") if isinstance(job.get("run_state"), dict) else {}
    if status == "running":
        return bool(run_state.get("running"))
    if status == "failed":
        effective_status = run_state.get("effective_status")
        if effective_status == "orphaned":
            return True
        latest_status = run_state.get("latest_status")
        return latest_status in {"failed", "partial"}
    return True


def _cron_job_metrics(jobs: list[dict[str, Any]]) -> dict[str, int]:
    metrics = {"total": 0, "scheduled": 0, "paused": 0, "failed": 0, "running": 0}
    for job in jobs:
        metrics["total"] += 1
        if job.get("status") == "paused":
            metrics["paused"] += 1
        else:
            metrics["scheduled"] += 1
        if _job_matches_status(job, "running"):
            metrics["running"] += 1
        if _job_matches_status(job, "failed"):
            metrics["failed"] += 1
    return metrics


def _paginate_jobs(jobs: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    safe_page = max(1, int(page or 1))
    safe_page_size = max(1, min(int(page_size or 20), 100))
    total = len(jobs)
    page_count = max(1, (total + safe_page_size - 1) // safe_page_size)
    safe_page = min(safe_page, page_count)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return jobs[start:end], {
        "page": safe_page,
        "page_size": safe_page_size,
        "total": total,
        "page_count": page_count,
    }


def _cron_job_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "cron_expr": payload.get("cron_expr"),
        "host": payload.get("host"),
        "username": payload.get("username"),
        "agent_profile": payload.get("agent_profile"),
        "message": payload.get("message"),
        "inspection_cycle": payload.get("inspection_cycle") or "daily",
        "inspection_depth": payload.get("inspection_depth") or "standard",
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


def list_inspection_job_records_page(
    *,
    page: int = 1,
    page_size: int = 20,
    query: str = "",
    status: str = "all",
    manager=CronManager,
) -> dict[str, Any]:
    jobs = manager.get_all_jobs()
    metrics = _cron_job_metrics(jobs)
    filtered_jobs = [
        job
        for job in jobs
        if _job_matches_query(job, query) and _job_matches_status(job, status)
    ]
    page_jobs, pagination = _paginate_jobs(filtered_jobs, page, page_size)
    pagination["filtered_total"] = len(filtered_jobs)
    return {
        "jobs": page_jobs,
        "pagination": pagination,
        "metrics": metrics,
    }


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


def cancel_running_inspection_job_record(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return manager.cancel_running_job(job_id)
    except KeyError as exc:
        raise InspectionJobServiceError(404, "该计划当前没有正在执行的巡检。") from exc
    except Exception as exc:
        raise InspectionJobServiceError(400, str(exc)) from exc


async def run_inspection_job_record_now(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return await manager.run_job_now(job_id)
    except KeyError as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc


async def start_inspection_job_record_now(job_id: str, manager=CronManager) -> dict[str, Any]:
    try:
        return await manager.start_job_now(job_id)
    except KeyError as exc:
        raise InspectionJobServiceError(404, "未找到该计划。") from exc
