from fastapi import APIRouter, UploadFile, File
from connections.ssh_manager import ssh_manager
from fastapi.responses import StreamingResponse
from core.agent import chat_stream_agent
from api.errors import raise_http_error
from api.mappers import (
    chat_stream_agent_kwargs,
    cron_job_created_response_kwargs,
    cron_job_deleted_response_kwargs,
    cron_job_payload,
    cron_job_response_kwargs,
    cron_job_run_trigger_response_kwargs,
    cron_jobs_response_kwargs,
    chat_attachment_preview_response_kwargs,
    inspection_run_export_response_kwargs,
    inspection_run_report_response_kwargs,
    inspection_run_response_kwargs,
    inspection_run_summary_response_kwargs,
    inspection_runs_response_kwargs,
)
from api.system_info_routes import router as system_info_router
from api.knowledge_routes import router as knowledge_router
from api.alert_routes import router as alert_router
from api.dashboard_routes import router as dashboard_router
from api.protocol_verification_routes import router as protocol_verification_router
from api.notification_routes import router as notification_router
from api.config_routes import router as config_router
from api.approval_routes import router as approval_router
from api.connection_routes import router as connection_router
from api.skill_routes import router as skill_router
from api.asset_routes import router as asset_router
from api.session_runtime_routes import router as session_runtime_router
from api.session_history_routes import router as session_history_router
from api.session_profile_routes import router as session_profile_router
from api.session_webhook_routes import router as session_webhook_router
from api.custom_command_routes import router as custom_command_router
from api.inspection_template_routes import router as inspection_template_router
from core.chat_attachments import (
    CHAT_ATTACHMENT_MAX_SIZE,
    ChatAttachmentError,
    build_chat_attachment_preview,
)
from core.chat_session_service import (
    ChatSessionServiceError,
    start_session_chat_run,
)
from core.inspection_run_service import (
    InspectionRunServiceError,
    export_inspection_run_report_content,
    get_inspection_run_record,
    get_inspection_run_report_record,
    inspection_run_summary,
    list_inspection_run_records,
)
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
from api.schemas import (
    ChatRequest,
    CronAddRequest,
    ResponseModel,
)

import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(system_info_router)
router.include_router(knowledge_router)
router.include_router(alert_router)
router.include_router(dashboard_router)
router.include_router(protocol_verification_router)
router.include_router(notification_router)
router.include_router(config_router)
router.include_router(approval_router)
router.include_router(connection_router)
router.include_router(skill_router)
router.include_router(asset_router)
router.include_router(session_runtime_router)
router.include_router(session_history_router)
router.include_router(session_profile_router)
router.include_router(session_webhook_router)
router.include_router(custom_command_router)
router.include_router(inspection_template_router)


def _preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    try:
        return build_chat_attachment_preview(filename, content_type, content)
    except ChatAttachmentError as exc:
        raise_http_error(exc)


# ----------------- 路由接口 -----------------


@router.post("/chat")
async def ai_chat_with_system(req: ChatRequest):
    """
    【新功能】：前端流式对话接口 (Server-Sent Events)
    不再傻等 20 秒，实时推送 AI 的思维链、动作和总结。
    """
    logger.info(
        f"AI Stream Chat received: '{req.message}' for session {req.session_id} using model [{req.model_name}]"
    )

    try:
        run = start_session_chat_run(
            ssh_manager.active_sessions,
            req.session_id,
            lambda: chat_stream_agent(**chat_stream_agent_kwargs(req)),
        )
    except ChatSessionServiceError as exc:
        raise_http_error(exc)
    return StreamingResponse(run.subscribe(), media_type="text/event-stream")


@router.post("/chat/attachments/preview", response_model=ResponseModel)
async def preview_chat_attachment(file: UploadFile = File(...)):
    """Parse a small document for one-off chat context without ingesting it into the KB."""
    content = await file.read(CHAT_ATTACHMENT_MAX_SIZE + 1)
    attachment = _preview_attachment_content(
        file.filename or "",
        file.content_type or "application/octet-stream",
        content,
    )
    return ResponseModel(**chat_attachment_preview_response_kwargs(attachment))


# ----------------- OpenClaw 自动化巡检 (Cron Jobs) -----------------
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


@router.get("/cron/{job_id}/runs", response_model=ResponseModel)
async def list_cron_job_runs(job_id: str, limit: int = 50, asset_id: int | None = None):
    runs = list_inspection_run_records(job_id=job_id, limit=limit, asset_id=asset_id)
    return ResponseModel(**inspection_runs_response_kwargs(runs))


@router.get("/inspection-runs", response_model=ResponseModel)
async def list_inspection_runs(job_id: str | None = None, asset_id: int | None = None, limit: int = 50):
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

