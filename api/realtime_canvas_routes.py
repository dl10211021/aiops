from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from api.schema_models.common import ResponseModel
from core.realtime_canvas import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_INTERVAL_SECONDS,
    SUPPORTED_METRICS,
    CANVAS_KINDS,
    CANVAS_MODES,
    DEFAULT_CANVAS_AI_PROMPT,
    DEFAULT_PYTHON_COLLECTOR,
    render_canvas_export_html,
    realtime_canvas_manager,
)


router = APIRouter()


class RealtimeCanvasStartRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    kind: str = "metrics"
    mode: str = "realtime"
    metrics: list[str] = Field(default_factory=lambda: ["cpu", "memory", "disk", "top_process"])
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    duration_seconds: int = DEFAULT_DURATION_SECONDS
    title: str | None = None
    stop_existing: bool = True
    scripts: dict[str, str] | None = None
    collector_code: str | None = None
    canvas_spec: dict | None = None
    data_schema: dict | None = None
    html: str | None = None
    ai_prompt_template: str | None = None


class RealtimeCanvasExtendRequest(BaseModel):
    duration_seconds: int = 10 * 60


class RealtimeCanvasUpdateRequest(BaseModel):
    title: str | None = None
    metrics: list[str] | None = None
    interval_seconds: int | None = None
    duration_seconds: int | None = None
    stop_existing: bool | None = None
    scripts: dict[str, str] | None = None
    kind: str | None = None
    mode: str | None = None
    collector_code: str | None = None
    canvas_spec: dict | None = None
    data_schema: dict | None = None
    html: str | None = None
    ai_prompt_template: str | None = None


@router.get("/realtime-canvas/options", response_model=ResponseModel)
async def realtime_canvas_options():
    return ResponseModel(
        status="success",
        data={
            "metrics": [{"id": key, "label": label} for key, label in SUPPORTED_METRICS.items()],
            "kinds": [{"id": key, "label": label} for key, label in CANVAS_KINDS.items()],
            "modes": [{"id": key, "label": label} for key, label in CANVAS_MODES.items()],
            "intervals": [5, 10, 30, 60],
            "durations": [5 * 60, 15 * 60, 30 * 60, 60 * 60],
            "default_ai_prompt": DEFAULT_CANVAS_AI_PROMPT,
            "default_python_collector": DEFAULT_PYTHON_COLLECTOR,
        },
    )


@router.get("/realtime-canvas", response_model=ResponseModel)
async def list_realtime_canvases():
    return ResponseModel(status="success", data={"items": await realtime_canvas_manager.list_items()})


@router.get("/realtime-canvas/{canvas_id}", response_model=ResponseModel)
async def get_realtime_canvas(canvas_id: str):
    item = await realtime_canvas_manager.get_item(canvas_id)
    if not item:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    return ResponseModel(status="success", data={"item": item})


@router.post("/realtime-canvas/start", response_model=ResponseModel)
async def start_realtime_canvas(req: RealtimeCanvasStartRequest):
    try:
        item = await realtime_canvas_manager.start(
            session_id=req.session_id,
            metrics=req.metrics,
            interval_seconds=req.interval_seconds,
            duration_seconds=req.duration_seconds,
            title=req.title,
            stop_existing=req.stop_existing,
            scripts=req.scripts,
            kind=req.kind,
            mode=req.mode,
            collector_code=req.collector_code,
            canvas_spec=req.canvas_spec,
            data_schema=req.data_schema,
            html=req.html,
            ai_prompt_template=req.ai_prompt_template,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResponseModel(status="success", data={"item": item}, message="实时画板已启动")


@router.post("/realtime-canvas/{canvas_id}/stop", response_model=ResponseModel)
async def stop_realtime_canvas(canvas_id: str):
    item = await realtime_canvas_manager.stop(canvas_id, reason="人工暂停。")
    if not item:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    return ResponseModel(status="success", data={"item": item}, message="实时画板已暂停")


@router.patch("/realtime-canvas/{canvas_id}", response_model=ResponseModel)
async def update_realtime_canvas(canvas_id: str, req: RealtimeCanvasUpdateRequest):
    item = await realtime_canvas_manager.update(
        canvas_id,
        req.model_dump(exclude_unset=True),
    )
    if not item:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    if req.ai_prompt_template:
        item = await realtime_canvas_manager.schedule_ai_generation(canvas_id) or item
    return ResponseModel(status="success", data={"item": item}, message="实时画板已更新")


@router.get("/realtime-canvas/{canvas_id}/export.html", response_class=HTMLResponse)
async def export_realtime_canvas_html(canvas_id: str):
    item = await realtime_canvas_manager.get_item(canvas_id)
    if not item:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    return HTMLResponse(
        content=render_canvas_export_html(item),
        headers={"Content-Disposition": f'attachment; filename="{canvas_id}.html"'},
    )


@router.delete("/realtime-canvas/{canvas_id}", response_model=ResponseModel)
async def delete_realtime_canvas(canvas_id: str):
    deleted = await realtime_canvas_manager.delete(canvas_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    return ResponseModel(status="success", data={}, message="实时画板已删除")


@router.post("/realtime-canvas/{canvas_id}/extend", response_model=ResponseModel)
async def extend_realtime_canvas(canvas_id: str, req: RealtimeCanvasExtendRequest):
    item = await realtime_canvas_manager.extend(canvas_id, req.duration_seconds)
    if not item:
        raise HTTPException(status_code=404, detail="实时画板不存在")
    return ResponseModel(status="success", data={"item": item}, message="实时画板已续期")
