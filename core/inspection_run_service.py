from __future__ import annotations

import json
from typing import Any

from core.inspection_results import (
    build_report,
    export_report_markdown,
    get_run,
    list_runs,
    run_summary,
)


class InspectionRunServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_inspection_run_records(
    job_id: str | None = None,
    asset_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return list_runs(job_id=job_id, asset_id=asset_id, limit=limit)


def inspection_run_summary() -> dict[str, Any]:
    return run_summary()


def get_inspection_run_record(run_id: str) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        raise InspectionRunServiceError(404, "巡检运行记录不存在")
    return run


def get_inspection_run_report_record(run_id: str) -> dict[str, Any]:
    report = build_report(run_id)
    if not report:
        raise InspectionRunServiceError(404, "巡检报告不存在")
    return report


def export_inspection_run_report_content(
    run_id: str,
    format: str = "markdown",
) -> dict[str, Any]:
    normalized = str(format or "markdown").lower()
    if normalized in {"md", "markdown"}:
        content = export_report_markdown(run_id)
        content_type = "text/markdown"
    elif normalized == "json":
        report = build_report(run_id)
        content = json.dumps(report, ensure_ascii=False, indent=2) if report else None
        content_type = "application/json"
    else:
        raise InspectionRunServiceError(422, "format 仅支持 markdown 或 json")
    if content is None:
        raise InspectionRunServiceError(404, "巡检报告不存在")
    return {
        "format": normalized,
        "content_type": content_type,
        "content": content,
    }
