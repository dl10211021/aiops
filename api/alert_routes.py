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
from api.schema_models.alerts import (
    AlertEventUpdateRequest,
    AlertPolicyTestRequest,
    AlertPolicyUpdateRequest,
    AlertWorkflowMessageRequest,
)
from api.schema_models.common import ResponseModel
from core.alert_event_service import (
    AlertEventServiceError,
    get_alert_event_record,
    list_alert_event_records,
    update_alert_event_record,
)
from core.alert_webhook_service import handle_alert_webhook, read_alert_webhook_payload
from core.alert_policy import (
    explain_alert_policy_for_payload,
    get_alert_automation_policy,
    save_alert_automation_policy,
)
from core.alert_workflows import (
    append_alert_workflow_message,
    ensure_alert_workflow,
    get_alert_workflow,
    trigger_alert_workflow_readonly_analysis,
)


router = APIRouter()
webhook_locks = {}


@router.get("/alerts", response_model=ResponseModel)
async def list_alert_events(
    status: str | None = None,
    severity: str | None = None,
    host: str | None = None,
    source_family: str | None = None,
    automation_mode: str | None = None,
    limit: int = 200,
):
    """查询告警事件。"""
    return ResponseModel(
        **alert_events_response_kwargs(
            list_alert_event_records(
                **alert_event_list_query_kwargs(status, severity, host, source_family, automation_mode, limit)
            )
        )
    )


@router.get("/alerts/policy", response_model=ResponseModel)
async def get_alert_policy():
    """查询告警自动化策略配置。"""
    return ResponseModel(status="success", data={"policy": get_alert_automation_policy()})


@router.post("/alerts/policy", response_model=ResponseModel)
async def update_alert_policy(req: AlertPolicyUpdateRequest):
    """保存告警自动化策略配置。"""
    return ResponseModel(status="success", data={"policy": save_alert_automation_policy(req.policy)})


@router.post("/alerts/policy/test", response_model=ResponseModel)
async def test_alert_policy(req: AlertPolicyTestRequest):
    """用样例告警测试会命中的自动化策略。"""
    return ResponseModel(status="success", data={"result": explain_alert_policy_for_payload(req.payload)})


@router.get("/alerts/{alert_id}/workflow", response_model=ResponseModel)
async def get_alert_workflow_record(alert_id: str):
    """查询告警工作流记录；没有记录时按当前告警现场生成一份。"""
    try:
        alert = get_alert_event_record(alert_id)
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    workflow = get_alert_workflow(alert_id)
    if workflow is None:
        workflow = ensure_alert_workflow(alert, active_sessions=ssh_manager.active_sessions)
    return ResponseModel(status="success", data={"workflow": workflow})


@router.post("/alerts/{alert_id}/workflow/messages", response_model=ResponseModel)
async def append_alert_workflow_message_record(alert_id: str, req: AlertWorkflowMessageRequest):
    """在告警工作流窗口追加人工消息。"""
    workflow = append_alert_workflow_message(alert_id, req.role, req.content)
    if workflow is None:
        try:
            alert = get_alert_event_record(alert_id)
        except AlertEventServiceError as exc:
            raise_http_error(exc)
        workflow = ensure_alert_workflow(alert, active_sessions=ssh_manager.active_sessions)
        workflow = append_alert_workflow_message(alert_id, req.role, req.content)
    return ResponseModel(status="success", data={"workflow": workflow})


@router.post("/alerts/{alert_id}/workflow/run-readonly", response_model=ResponseModel)
async def run_alert_workflow_readonly(alert_id: str):
    """手动触发告警工作流的只读 AI 分析，只联动当前在线资产会话。"""
    try:
        alert = get_alert_event_record(alert_id)
    except AlertEventServiceError as exc:
        raise_http_error(exc)
    result = await trigger_alert_workflow_readonly_analysis(
        alert,
        active_sessions=ssh_manager.active_sessions,
        session_locks=webhook_locks,
    )
    return ResponseModel(status="success", message=result["message"], data=result)


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
