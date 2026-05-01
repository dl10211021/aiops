from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

from core.approval_queue import resolve_approval_request

logger = logging.getLogger(__name__)


class SessionInteractionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def approve_session_tool_call(
    active_sessions: MutableMapping[str, dict[str, Any]],
    dispatcher: Any,
    session_id: str,
    tool_call_id: str,
    *,
    approved: bool,
    auto_approve_all: bool = False,
    operator: str | None = "user",
    note: str | None = "",
) -> dict[str, Any]:
    if auto_approve_all and session_id in active_sessions:
        active_sessions[session_id]["info"]["auto_approve_all"] = True
        logger.info("Session %s set to auto-approve all tools.", session_id)

    future = dispatcher.pending_approvals.get(tool_call_id)
    if future and not future.done():
        future.set_result(approved)
        try:
            resolve_approval_request(
                tool_call_id,
                approved=approved,
                operator=operator or "user",
                note=note or "",
            )
        except KeyError:
            pass
        return {
            "message": "Approval action submitted.",
            "approval": None,
            "include_approval": False,
        }

    try:
        approval = resolve_approval_request(
            tool_call_id,
            approved=approved,
            operator=operator or "user",
            note=note or "",
        )
    except KeyError as exc:
        raise SessionInteractionServiceError(
            404,
            "Pending tool call not found or already processed.",
        ) from exc

    return {
        "message": "Approval action recorded.",
        "approval": approval,
        "include_approval": True,
    }


def submit_user_interaction_response(
    dispatcher: Any,
    session_id: str,
    request_id: str,
    *,
    value: str | None = "",
    label: str | None = "",
) -> dict[str, str]:
    entry = dispatcher.pending_interactions.get(request_id)
    future = entry.get("future") if isinstance(entry, dict) else entry
    expected_session_id = entry.get("session_id") if isinstance(entry, dict) else None
    if expected_session_id and expected_session_id != session_id:
        raise SessionInteractionServiceError(404, "交互请求不存在、已提交或已超时。")

    if future and not future.done():
        response = {"value": value or "", "label": label or ""}
        future.set_result(response)
        return response

    raise SessionInteractionServiceError(404, "交互请求不存在、已提交或已超时。")
