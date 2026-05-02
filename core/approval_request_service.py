from __future__ import annotations

from typing import Any

from core import dispatcher as dispatcher_module
from core.approval_queue import (
    get_approval_request,
    list_approval_requests,
    resolve_approval_request,
)


class ApprovalRequestServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def list_approval_request_records(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return list_approval_requests(status=status, limit=limit)


def get_approval_request_record(approval_id: str) -> dict[str, Any]:
    approval = get_approval_request(approval_id)
    if not approval:
        raise ApprovalRequestServiceError(404, "审批请求不存在")
    return approval


def decide_approval_request_record(
    approval_id: str,
    *,
    approved: bool,
    operator: str | None = "user",
    note: str | None = "",
    dispatcher: Any | None = None,
) -> dict[str, Any]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    future = resolved_dispatcher.pending_approvals.get(approval_id)
    if future and not future.done():
        future.set_result(approved)
    try:
        return resolve_approval_request(
            approval_id,
            approved=approved,
            operator=operator or "user",
            note=note or "",
        )
    except KeyError as exc:
        raise ApprovalRequestServiceError(404, "审批请求不存在") from exc
