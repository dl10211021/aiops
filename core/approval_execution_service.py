from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from core.approval_queue import get_approval_request

RollbackExecutor = Callable[[str, str, str, str], Awaitable[Any]]


class ApprovalExecutionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class ApprovalExecutionResult:
    status: str
    message: str
    approval: dict[str, Any]
    result: Any


def _load_executable_rollback_approval(approval_id: str) -> tuple[dict[str, Any], str, str, str]:
    approval = get_approval_request(approval_id)
    if not approval:
        raise ApprovalExecutionServiceError(404, "审批请求不存在")
    if approval.get("status") != "approved":
        raise ApprovalExecutionServiceError(409, "审批尚未批准，不能执行。")
    if approval.get("execution"):
        raise ApprovalExecutionServiceError(409, "该审批已经执行过。")
    if approval.get("tool_name") != "rollback_skill":
        raise ApprovalExecutionServiceError(422, "该审批类型暂不支持直接执行。")

    args = approval.get("args") or {}
    skill_id = str(args.get("skill_id") or "").strip()
    file_name = str(args.get("file_name") or "").strip()
    version_id = str(args.get("version_id") or "").strip()
    if not skill_id or not file_name or not version_id:
        raise ApprovalExecutionServiceError(422, "审批参数不完整，无法执行技能回滚。")

    return approval, skill_id, file_name, version_id


async def execute_approval_request_action(
    approval_id: str,
    rollback_executor: RollbackExecutor,
) -> ApprovalExecutionResult:
    approval, skill_id, file_name, version_id = _load_executable_rollback_approval(approval_id)
    response = await rollback_executor(skill_id, file_name, version_id, approval_id)
    executed_approval = get_approval_request(approval_id)
    return ApprovalExecutionResult(
        status=getattr(response, "status", "success"),
        message=getattr(response, "message", "") or "审批动作已执行。",
        approval=executed_approval or approval,
        result=getattr(response, "data", None),
    )
