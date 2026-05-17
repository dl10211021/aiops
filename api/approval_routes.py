from pathlib import Path

from fastapi import APIRouter

from connections.ssh_manager import ssh_manager
from api.errors import raise_http_error
from api.response_mappers.approvals import (
    approval_audit_summary_response_kwargs,
    approval_decision_response_kwargs,
    approval_execution_response_kwargs,
    approval_request_response_kwargs,
    approval_requests_response_kwargs,
    tool_approval_response_kwargs,
    user_interaction_submitted_response_kwargs,
)
from api.schema_models.approvals import (
    ApprovalDecisionRequest,
    ToolApprovalRequest,
    UserInteractionResponseRequest,
)
from api.schema_models.common import ResponseModel
from core.approval_execution_service import (
    ApprovalExecutionServiceError,
    execute_custom_skill_rollback_approval,
)
from core.approval_request_service import (
    ApprovalRequestServiceError,
    decide_approval_request_record,
    get_approval_audit_summary_record,
    get_approval_request_record,
    list_approval_request_records,
)
from core.session_interaction_service import (
    SessionInteractionServiceError,
    approve_session_tool_call,
    submit_user_interaction_response,
)


CUSTOM_SKILLS_DIR = Path(__file__).resolve().parent.parent / "my_custom_skills"
router = APIRouter()


@router.post("/session/{session_id}/approve", response_model=ResponseModel)
async def approve_tool_call(session_id: str, req: ToolApprovalRequest):
    """【新功能】用户确认是否允许 AI 执行敏感指令"""
    try:
        result = approve_session_tool_call(
            ssh_manager.active_sessions,
            session_id,
            req.tool_call_id,
            approved=req.approved,
            auto_approve_all=req.auto_approve_all,
            operator=req.operator or "user",
            note=req.note or "",
        )
    except SessionInteractionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**tool_approval_response_kwargs(result))


@router.post("/session/{session_id}/interaction", response_model=ResponseModel)
async def respond_user_interaction(session_id: str, req: UserInteractionResponseRequest):
    """提交前台聊天中的文本、密码或选项交互响应。"""
    try:
        submit_user_interaction_response(
            session_id,
            req.request_id,
            value=req.value,
            label=req.label,
        )
    except SessionInteractionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**user_interaction_submitted_response_kwargs())


@router.get("/approvals", response_model=ResponseModel)
async def list_approval_requests(status: str | None = None, limit: int = 100):
    """查询高危工具调用审批队列。"""
    return ResponseModel(
        **approval_requests_response_kwargs(
            list_approval_request_records(status=status, limit=limit)
        )
    )


@router.get("/approvals/summary", response_model=ResponseModel)
async def get_approval_summary(limit: int = 500):
    """查询审批策略执行审计聚合。"""
    return ResponseModel(
        **approval_audit_summary_response_kwargs(
            get_approval_audit_summary_record(limit=limit)
        )
    )


@router.get("/approvals/{approval_id}", response_model=ResponseModel)
async def get_approval_request(approval_id: str):
    """查询单个审批请求。"""
    try:
        approval = get_approval_request_record(approval_id)
    except ApprovalRequestServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**approval_request_response_kwargs(approval))


@router.post("/approvals/{approval_id}/decision", response_model=ResponseModel)
async def decide_approval_request(approval_id: str, req: ApprovalDecisionRequest):
    """审批或拒绝高危工具调用，并写入审计状态。"""
    try:
        approval = decide_approval_request_record(
            approval_id,
            approved=req.approved,
            operator=req.operator or "user",
            note=req.note or "",
        )
    except ApprovalRequestServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**approval_decision_response_kwargs(approval))


@router.post("/approvals/{approval_id}/execute", response_model=ResponseModel)
async def execute_approval_request(approval_id: str):
    """执行已经批准且支持后续执行的审批请求。"""
    try:
        result = await execute_custom_skill_rollback_approval(
            approval_id,
            base_dir=CUSTOM_SKILLS_DIR,
        )
    except ApprovalExecutionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**approval_execution_response_kwargs(result))
