import asyncio

from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.inspection import (
    cron_job_created_response_kwargs,
    cron_job_deleted_response_kwargs,
    cron_job_payload,
    cron_job_response_kwargs,
    cron_job_run_trigger_response_kwargs,
    cron_jobs_response_kwargs,
)
from api.schemas import CronAddRequest, ResponseModel
from core.inspection_job_service import (
    InspectionJobServiceError,
    create_inspection_job_record,
    list_inspection_job_records,
    pause_inspection_job_record,
    remove_inspection_job_record,
    resume_inspection_job_record,
    run_inspection_job_record_now,
    update_inspection_job_record,
)


router = APIRouter()


@router.post("/cron/add", response_model=ResponseModel)
async def add_cron_job(req: CronAddRequest):
    """【新功能】添加大模型定时巡检任务 (类似 openclaw cron add)"""
    try:
        payload = create_inspection_job_record(cron_job_payload(req))
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_created_response_kwargs(payload))


@router.get("/cron/list", response_model=ResponseModel)
async def list_cron_jobs():
    """【新功能】查看所有的定时巡检计划"""
    jobs = await asyncio.to_thread(list_inspection_job_records)
    return ResponseModel(**cron_jobs_response_kwargs(jobs))


@router.delete("/cron/{job_id}", response_model=ResponseModel)
async def delete_cron_job(job_id: str):
    """【新功能】删除某个定时巡检计划"""
    try:
        await asyncio.to_thread(remove_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_deleted_response_kwargs(job_id))


@router.put("/cron/{job_id}", response_model=ResponseModel)
async def update_cron_job(job_id: str, req: CronAddRequest):
    try:
        job = await asyncio.to_thread(
            update_inspection_job_record,
            job_id,
            cron_job_payload(req),
        )
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_response_kwargs(job, "巡检计划已更新"))


@router.post("/cron/{job_id}/pause", response_model=ResponseModel)
async def pause_cron_job(job_id: str):
    try:
        job = await asyncio.to_thread(pause_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_response_kwargs(job, "巡检计划已暂停"))


@router.post("/cron/{job_id}/resume", response_model=ResponseModel)
async def resume_cron_job(job_id: str):
    try:
        job = await asyncio.to_thread(resume_inspection_job_record, job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_response_kwargs(job, "巡检计划已恢复"))


@router.post("/cron/{job_id}/run", response_model=ResponseModel)
async def run_cron_job_now(job_id: str):
    try:
        result = await run_inspection_job_record_now(job_id)
    except InspectionJobServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**cron_job_run_trigger_response_kwargs(result))
