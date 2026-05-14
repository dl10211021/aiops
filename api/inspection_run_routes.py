from fastapi import APIRouter, Query

from api.errors import raise_http_error
from api.response_mappers.inspection import (
    inspection_run_deleted_response_kwargs,
    inspection_run_export_response_kwargs,
    inspection_run_report_response_kwargs,
    inspection_run_retention_preview_response_kwargs,
    inspection_run_response_kwargs,
    inspection_run_summary_response_kwargs,
    inspection_runs_response_kwargs,
)
from api.schema_models.common import ResponseModel
from core.inspection_run_service import (
    InspectionRunServiceError,
    delete_inspection_run_record,
    export_inspection_run_report_content,
    get_inspection_run_record,
    get_inspection_run_report_record,
    inspection_run_summary,
    list_inspection_run_record_page,
    list_inspection_run_records,
    preview_inspection_run_retention,
)


router = APIRouter()


@router.get("/cron/{job_id}/runs", response_model=ResponseModel)
async def list_cron_job_runs(job_id: str, limit: int = 50, asset_id: int | None = None):
    runs = list_inspection_run_records(job_id=job_id, limit=limit, asset_id=asset_id)
    return ResponseModel(**inspection_runs_response_kwargs(runs))


@router.get("/inspection-runs", response_model=ResponseModel)
async def list_inspection_runs(
    job_id: str | None = None,
    asset_id: int | None = None,
    limit: int = 50,
    page: int = 1,
    page_size: int = 50,
    query: str | None = None,
    status: str | None = None,
):
    result = list_inspection_run_record_page(
        job_id=job_id,
        asset_id=asset_id,
        limit=limit,
        page=page,
        page_size=page_size,
        query=query,
        status=status,
    )
    return ResponseModel(
        **inspection_runs_response_kwargs(
            result["runs"],
            pagination=result["pagination"],
            metrics=result["metrics"],
        )
    )


@router.get("/cron/runs/summary", response_model=ResponseModel)
async def get_cron_run_summary():
    return ResponseModel(**inspection_run_summary_response_kwargs(inspection_run_summary()))


@router.get("/inspection-runs/retention/preview", response_model=ResponseModel)
async def preview_inspection_run_retention_policy(
    keep_latest_per_job: int = Query(default=20, ge=1, le=500),
    older_than_days: int = Query(default=90, ge=1, le=3650),
    limit: int = Query(default=100, ge=1, le=500),
):
    preview = preview_inspection_run_retention(
        keep_latest_per_job=keep_latest_per_job,
        older_than_days=older_than_days,
        limit=limit,
    )
    return ResponseModel(**inspection_run_retention_preview_response_kwargs(preview))


@router.get("/cron/runs/{run_id}", response_model=ResponseModel)
async def get_cron_job_run(run_id: str):
    try:
        run = get_inspection_run_record(run_id)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**inspection_run_response_kwargs(run))


@router.delete("/inspection-runs/{run_id}", response_model=ResponseModel)
async def delete_inspection_run(run_id: str):
    try:
        delete_inspection_run_record(run_id)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**inspection_run_deleted_response_kwargs(run_id))


@router.get("/inspection-runs/{run_id}/report", response_model=ResponseModel)
async def get_inspection_run_report(run_id: str):
    try:
        report = get_inspection_run_report_record(run_id)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**inspection_run_report_response_kwargs(report))


@router.get("/inspection-runs/{run_id}/export", response_model=ResponseModel)
async def export_inspection_run_report(run_id: str, format: str = "markdown"):
    try:
        payload = export_inspection_run_report_content(run_id, format)
    except InspectionRunServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**inspection_run_export_response_kwargs(payload))
