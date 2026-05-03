from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, AsyncIterator
from typing import Any, Protocol

from core.agent_approval import record_tool_approval_request
from core.agent_interactions import (
    _build_interaction_payload,
    _wait_for_user_interaction,
)
from core.agent_sse import sse_event, sse_raw
from core.agent_tool_events import (
    build_tool_end_event,
    invalid_tool_arguments_result,
    prepare_tool_call,
)
from core.safety_policy import approval_timeout_seconds


class ChatMemoryStore(Protocol):
    def append_message(self, session_id: str, message: dict) -> None:
        ...


async def process_chat_tool_calls(
    *,
    tool_calls: list[dict],
    session_id: str,
    messages: list[dict],
    memory_store: ChatMemoryStore,
    dispatcher: Any,
    context: dict,
    iteration: int,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> AsyncIterator[str]:
    for tc in tool_calls:
        prepared_call = prepare_tool_call(tc)
        func_name = prepared_call.name
        func_args = prepared_call.args
        display_cmd = prepared_call.display_cmd
        tc_id = prepared_call.id

        if prepared_call.parse_error:
            tool_res = invalid_tool_arguments_result(prepared_call.parse_error)
            msg_end, safe_tool_res = build_tool_end_event(tc_id, func_name, tool_res)
            yield sse_raw(msg_end)
            tool_msg = {
                "tool_call_id": tc_id,
                "role": "tool",
                "name": func_name,
                "content": safe_tool_res,
            }
            messages.append(tool_msg)
            memory_store.append_message(session_id, tool_msg)
            continue

        if func_name == "request_user_interaction":
            payload = _build_interaction_payload(tc_id, func_args)
            future = asyncio.Future()
            dispatcher.pending_interactions[tc_id] = {
                "future": future,
                "session_id": session_id,
            }
            yield sse_event(payload, ensure_ascii=False)
            tool_res, safe_tool_res = await _wait_for_user_interaction(
                tc_id,
                payload,
                future,
            )
            tool_msg = {
                "tool_call_id": tc_id,
                "role": "tool",
                "name": func_name,
                "content": tool_res,
            }
            messages.append(tool_msg)
            try:
                interaction_result = json.loads(safe_tool_res)
            except Exception:
                interaction_result = {}
            interaction_done = json.dumps(
                {
                    "type": "user_interaction_done",
                    "request_id": tc_id,
                    "status": interaction_result.get("status") or "submitted",
                    "input_type": payload["input_type"],
                    "value": interaction_result.get("value") or "",
                    "label": interaction_result.get("label") or "",
                },
                ensure_ascii=False,
            )
            yield sse_raw(interaction_done)
            memory_store.append_message(
                session_id,
                {
                    "tool_call_id": tc_id,
                    "role": "tool",
                    "name": func_name,
                    "content": safe_tool_res,
                },
            )
            continue

        needs_approval, reason = dispatcher.check_approval_needed(
            func_name,
            func_args,
            context,
        )
        approval_required = False

        if needs_approval:
            approval_required = True
            approval_record = record_tool_approval_request(
                tool_call_id=tc_id,
                session_id=session_id,
                tool_name=func_name,
                args=func_args,
                reason=reason,
                context=context,
            )
            policy_metadata = (approval_record.get("metadata") or {}).get("policy") or {}
            msg_ask = json.dumps(
                {
                    "type": "tool_ask_approval",
                    "tool_call_id": tc_id,
                    "tool_name": func_name,
                    "args": display_cmd,
                    "reason": reason,
                    "actions": policy_metadata.get("actions") or [],
                    "primary_action": policy_metadata.get("primary_action"),
                    "id": tc_id,
                    "tool": func_name,
                    "cmd": display_cmd,
                }
            )
            yield sse_raw(msg_ask)

            future = asyncio.Future()
            dispatcher.pending_approvals[tc_id] = future
            approval_timed_out = False
            try:
                approved = await asyncio.wait_for(
                    future,
                    timeout=float(approval_timeout_seconds()),
                )
            except asyncio.TimeoutError:
                approved = False
                approval_timed_out = True
                try:
                    from core.approval_queue import mark_approval_timeout

                    mark_approval_timeout(tc_id)
                except KeyError:
                    pass

            if tc_id in dispatcher.pending_approvals:
                del dispatcher.pending_approvals[tc_id]

            if not approved:
                tool_res = json.dumps(
                    {
                        "status": "BLOCKED",
                        "error_type": (
                            "approval_timeout"
                            if approval_timed_out
                            else "approval_rejected"
                        ),
                        "error": (
                            "审批超时，工具调用已取消。"
                            if approval_timed_out
                            else "用户拒绝执行该工具调用。"
                        ),
                        "hint": (
                            "如仍需执行，请重新发送任务并完成审批。"
                            if approval_timed_out
                            else "如需再次执行，请重新发送任务并选择批准。"
                        ),
                    },
                    ensure_ascii=False,
                )
                msg_end, safe_tool_res = build_tool_end_event(
                    tc_id,
                    func_name,
                    tool_res,
                )
                yield sse_raw(msg_end)

                tool_msg = {
                    "tool_call_id": tc_id,
                    "role": "tool",
                    "name": func_name,
                    "content": safe_tool_res,
                }
                messages.append(tool_msg)
                memory_store.append_message(session_id, tool_msg)
                continue

        msg_start = json.dumps(
            {
                "type": "tool_start",
                "id": tc_id,
                "tool": func_name,
                "cmd": display_cmd,
            }
        )
        yield sse_raw(msg_start)
        await sleep(0.05)

        tool_res = await dispatcher.route_and_execute(func_name, func_args, context)
        if approval_required:
            try:
                from core.approval_queue import record_approval_execution

                record_approval_execution(tc_id, tool_res)
            except KeyError:
                pass
        msg_end, safe_tool_res = build_tool_end_event(tc_id, func_name, tool_res)
        yield sse_raw(msg_end)
        await sleep(0.05)

        tool_msg = {
            "tool_call_id": tc_id,
            "role": "tool",
            "name": func_name,
            "content": safe_tool_res,
        }
        messages.append(tool_msg)
        memory_store.append_message(session_id, tool_msg)

    msg_loop = json.dumps(
        {
            "type": "status",
            "content": f"🔄 收集结果，执行第 {iteration + 2} 步...",
        }
    )
    yield sse_raw(msg_loop)
    await sleep(0.05)
