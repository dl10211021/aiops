from __future__ import annotations

from typing import Any

from api.schema_models.inspection import CronAddRequest, InspectionTemplatePayload


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


def cron_jobs_response_kwargs(
    jobs: list[Any],
    pagination: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"jobs": jobs}
    if pagination is not None:
        data["pagination"] = pagination
    if metrics is not None:
        data["metrics"] = metrics
    return {
        "status": "success",
        "data": data,
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


def cron_job_run_cancel_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "正在取消当前巡检运行",
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


def inspection_run_deleted_response_kwargs(run_id: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"巡检报告 {run_id} 已删除",
        "data": {"run_id": run_id},
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
