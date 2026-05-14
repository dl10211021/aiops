from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, AsyncIterator
from typing import Any, Protocol

from core.agent_approval import record_tool_approval_request
from core.agent_interactions import (
    _build_interaction_payload,
    _wait_for_user_interaction,
)
from core.agent_sse import sse_event, sse_raw
from core.agent_tool_events import (
    PreparedToolCall,
    build_tool_end_event,
    invalid_tool_arguments_result,
    prepare_tool_call,
)
from core.safety_policy import approval_timeout_seconds
from core.tool_execution_policy import (
    evaluate_tool_execution_gate,
    execute_with_runtime_policy,
)
from core.tool_registry import tool_policy_metadata


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
    trace_collector: Callable[[dict], None] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> AsyncIterator[str]:
    index = 0
    while index < len(tool_calls):
        concurrent_plan = _build_concurrent_plan(
            tool_calls,
            dispatcher,
            context,
            start_index=index,
        )
        if concurrent_plan:
            async for event in _process_concurrent_tool_calls(
                concurrent_plan,
                session_id=session_id,
                messages=messages,
                memory_store=memory_store,
                dispatcher=dispatcher,
                context=context,
                trace_collector=trace_collector,
                sleep=sleep,
            ):
                yield event
            index += len(concurrent_plan)
            continue

        tc = tool_calls[index]
        index += 1
        prepared_call = prepare_tool_call(tc)
        func_name = prepared_call.name
        func_args = prepared_call.args
        display_cmd = prepared_call.display_cmd
        tc_id = prepared_call.id

        if prepared_call.parse_error:
            tool_res = invalid_tool_arguments_result(prepared_call.parse_error)
            finished_at = int(time.time() * 1000)
            msg_end, safe_tool_res = build_tool_end_event(
                tc_id,
                func_name,
                tool_res,
                session_id=session_id,
                context=context,
                input_summary=display_cmd,
                finished_at=finished_at,
            )
            _collect_tool_end_trace(trace_collector, msg_end)
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

        if func_name in {"request_user_interaction", "clarify"}:
            interaction_args = func_args
            if func_name == "clarify":
                choices = func_args.get("choices")
                interaction_args = {
                    "prompt": func_args.get("question") or "请补充信息",
                    "input_type": "choice" if isinstance(choices, list) and choices else "text",
                    "options": choices or [],
                    "timeout_seconds": func_args.get("timeout_seconds") or 300,
                }
            payload = _build_interaction_payload(tc_id, interaction_args)
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
        tool_policy = tool_policy_metadata(func_name)
        execution_gate = evaluate_tool_execution_gate(
            func_name,
            safety_needs_approval=needs_approval,
            safety_reason=reason,
            policy=tool_policy,
        )
        needs_approval = execution_gate.approval_required
        reason = execution_gate.reason

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
                    "tool_policy": tool_policy,
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
                finished_at = int(time.time() * 1000)
                msg_end, safe_tool_res = build_tool_end_event(
                    tc_id,
                    func_name,
                    tool_res,
                    session_id=session_id,
                    context=context,
                    input_summary=display_cmd,
                    finished_at=finished_at,
                    approval_ref=tc_id,
                )
                _collect_tool_end_trace(trace_collector, msg_end)
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

        started_at = int(time.time() * 1000)
        msg_start = json.dumps(
            {
                "type": "tool_start",
                "id": tc_id,
                "tool": func_name,
                "args": display_cmd,
                "cmd": display_cmd,
                "result_meta": {"tool_policy": tool_policy},
                "started_at": started_at,
            }
        )
        if trace_collector:
            trace_collector(
                {
                    "type": "tool_start",
                    "toolCallId": tc_id,
                    "tool": func_name,
                    "args": display_cmd,
                    "resultMeta": {"tool_policy": tool_policy},
                    "startedAt": started_at,
                }
            )
        yield sse_raw(msg_start)
        await sleep(0.05)

        tool_res = await execute_with_runtime_policy(
            func_name,
            lambda: dispatcher.route_and_execute(func_name, func_args, context),
            policy=tool_policy,
        )
        if approval_required:
            try:
                from core.approval_queue import record_approval_execution

                record_approval_execution(tc_id, tool_res)
            except KeyError:
                pass
        finished_at = int(time.time() * 1000)
        msg_end, safe_tool_res = build_tool_end_event(
            tc_id,
            func_name,
            tool_res,
            session_id=session_id,
            context=context,
            input_summary=display_cmd,
            started_at=started_at,
            finished_at=finished_at,
            approval_ref=tc_id if approval_required else None,
        )
        _collect_tool_end_trace(trace_collector, msg_end)
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


def _build_concurrent_plan(
    tool_calls: list[dict],
    dispatcher: Any,
    context: dict,
    *,
    start_index: int = 0,
) -> list[dict[str, Any]] | None:
    if len(tool_calls) - start_index < 2:
        return None
    prepared: list[dict[str, Any]] = []
    for tc in tool_calls[start_index:]:
        prepared_call = prepare_tool_call(tc)
        if prepared_call.parse_error or prepared_call.name in {"request_user_interaction", "clarify"}:
            break
        tool_policy = tool_policy_metadata(prepared_call.name)
        if not tool_policy.get("concurrency_safe"):
            break
        needs_approval, reason = dispatcher.check_approval_needed(
            prepared_call.name,
            prepared_call.args,
            context,
        )
        gate = evaluate_tool_execution_gate(
            prepared_call.name,
            safety_needs_approval=needs_approval,
            safety_reason=reason,
            policy=tool_policy,
        )
        if gate.approval_required:
            break
        prepared.append({"call": prepared_call, "policy": tool_policy})

    if len(prepared) < 2:
        return None
    return prepared


async def _process_concurrent_tool_calls(
    plan: list[dict[str, Any]],
    *,
    session_id: str,
    messages: list[dict],
    memory_store: ChatMemoryStore,
    dispatcher: Any,
    context: dict,
    trace_collector: Callable[[dict], None] | None,
    sleep: Callable[[float], Awaitable[None]],
) -> AsyncIterator[str]:
    started_at_by_id: dict[str, int] = {}
    for item in plan:
        prepared_call: PreparedToolCall = item["call"]
        tool_policy = item["policy"]
        started_at = int(time.time() * 1000)
        started_at_by_id[prepared_call.id] = started_at
        msg_start = json.dumps(
            {
                "type": "tool_start",
                "id": prepared_call.id,
                "tool": prepared_call.name,
                "args": prepared_call.display_cmd,
                "cmd": prepared_call.display_cmd,
                "result_meta": {"tool_policy": tool_policy, "concurrent": True},
                "started_at": started_at,
            }
        )
        if trace_collector:
            trace_collector(
                {
                    "type": "tool_start",
                    "toolCallId": prepared_call.id,
                    "tool": prepared_call.name,
                    "args": prepared_call.display_cmd,
                    "resultMeta": {"tool_policy": tool_policy, "concurrent": True},
                    "startedAt": started_at,
                }
            )
        yield sse_raw(msg_start)

    await sleep(0.05)

    async def run_tool(item: dict[str, Any]) -> Any:
        prepared_call: PreparedToolCall = item["call"]
        return await execute_with_runtime_policy(
            prepared_call.name,
            lambda: dispatcher.route_and_execute(prepared_call.name, prepared_call.args, context),
            policy=item["policy"],
        )

    results = await asyncio.gather(*(run_tool(item) for item in plan))
    for item, tool_res in zip(plan, results):
        prepared_call: PreparedToolCall = item["call"]
        finished_at = int(time.time() * 1000)
        msg_end, safe_tool_res = build_tool_end_event(
            prepared_call.id,
            prepared_call.name,
            tool_res,
            session_id=session_id,
            context=context,
            input_summary=prepared_call.display_cmd,
            started_at=started_at_by_id.get(prepared_call.id),
            finished_at=finished_at,
        )
        _collect_tool_end_trace(trace_collector, msg_end)
        yield sse_raw(msg_end)
        await sleep(0.05)

        tool_msg = {
            "tool_call_id": prepared_call.id,
            "role": "tool",
            "name": prepared_call.name,
            "content": safe_tool_res,
        }
        messages.append(tool_msg)
        memory_store.append_message(session_id, tool_msg)


def _collect_tool_end_trace(
    trace_collector: Callable[[dict], None] | None,
    raw_event: str,
) -> None:
    if not trace_collector:
        return
    try:
        payload = json.loads(raw_event)
    except Exception:
        return
    trace_collector(
        {
            "type": "tool_end",
            "toolCallId": payload.get("id") or payload.get("tool_call_id") or "",
            "tool": payload.get("tool") or "unknown",
            "result": payload.get("result") or "",
            "resultMeta": payload.get("result_meta") or {},
            "evidenceId": payload.get("evidence_id") or "",
            "evidence": payload.get("evidence") or {},
            "status": payload.get("result_status") or "done",
            "completedAt": payload.get("finished_at"),
        }
    )
