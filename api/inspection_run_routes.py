from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.inspection import (
    inspection_run_deleted_response_kwargs,
    inspection_run_export_response_kwargs,
    inspection_run_report_response_kwargs,
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
    list_inspection_run_records,
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
):
    runs = list_inspection_run_records(job_id=job_id, asset_id=asset_id, limit=limit)
    return ResponseModel(**inspection_runs_response_kwargs(runs))


@router.get("/cron/runs/summary", response_model=ResponseModel)
async def get_cron_run_summary():
    return ResponseModel(**inspection_run_summary_response_kwargs(inspection_run_summary()))


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
