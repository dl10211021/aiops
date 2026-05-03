from __future__ import annotations

import uuid

from core.safety_policy import approval_timeout_seconds


def record_tool_approval_request(
    *,
    tool_call_id: str,
    session_id: str,
    tool_name: str,
    args: dict,
    reason: str,
    context: dict,
) -> dict:
    from core.approval_queue import record_approval_request

    return record_approval_request(
        tool_call_id=tool_call_id,
        session_id=session_id,
        tool_name=tool_name,
        args=args,
        reason=reason,
        context=context,
        timeout_seconds=approval_timeout_seconds(),
    )


def record_headless_approval_block(
    *,
    tool_call_id: str,
    session_id: str,
    tool_name: str,
    args: dict,
    reason: str,
    context: dict,
) -> dict:
    """Audit and block approval-required tool calls from unattended runs."""
    approval_id = str(tool_call_id or "").strip() or f"headless-{uuid.uuid4().hex[:16]}"
    recorded = record_tool_approval_request(
        tool_call_id=approval_id,
        session_id=session_id,
        tool_name=tool_name,
        args=args,
        reason=reason,
        context={**(context or {}), "execution_mode": "headless"},
    )

    try:
        from core.approval_queue import resolve_approval_request

        return resolve_approval_request(
            approval_id,
            approved=False,
            operator="system",
            note="后台自治任务触发需审批工具调用，系统已自动阻断；请在前台人工确认后重试。",
        )
    except KeyError:
        return recorded
