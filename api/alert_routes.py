from fastapi import APIRouter, Request

from connections.ssh_manager import ssh_manager
from api.errors import raise_http_error
from api.response_mappers.alerts import (
    alert_event_list_query_kwargs,
    alert_event_response_kwargs,
    alert_event_update_kwargs,
    alert_events_response_kwargs,
    alert_webhook_response_kwargs,
)
from api.schemas import AlertEventUpdateRequest, ResponseModel
from core.alert_event_service import (
    AlertEventServiceError,
    get_alert_event_record,
    list_alert_event_records,
    update_alert_event_record,
)
from core.alert_webhook_service import handle_alert_webhook, read_alert_webhook_payload


router = APIRouter()
webhook_locks = {}


@router.get("/alerts", response_model=ResponseModel)
async def list_alert_events(
    status: str | None = None,
    severity: str | None = None,
    host: str | None = None,
    limit: int = 200,
):
    """查询告警事件。"""
    return ResponseModel(
        **alert_events_response_kwargs(
            list_alert_event_records(
                **alert_event_list_query_kwargs(status, severity, host, limit)
            )
        )
    )


@router.get("/alerts/{alert_id}", response_model=ResponseModel)
async def get_alert_event(alert_id: str):
    """查询单个告警事件。"""
    try:
        alert = get_alert_event_record(alert_id)
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**alert_event_response_kwargs(alert))


@router.patch("/alerts/{alert_id}", response_model=ResponseModel)
async def update_alert_event(alert_id: str, req: AlertEventUpdateRequest):
    """更新告警状态、处理人或备注。"""
    try:
        alert = update_alert_event_record(
            alert_id,
            **alert_event_update_kwargs(req),
        )
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**alert_event_response_kwargs(alert))


@router.post("/webhook/alert", response_model=ResponseModel)
async def receive_webhook_alert(request: Request):
    """【AIOps 高级特性】接收外部告警 (Prometheus / ManageEngine) 并推入相关 AI 会话"""
    payload = await read_alert_webhook_payload(request.json)

    result = await handle_alert_webhook(
        payload,
        ssh_manager.active_sessions,
        webhook_locks,
    )

    return ResponseModel(**alert_webhook_response_kwargs(result))
