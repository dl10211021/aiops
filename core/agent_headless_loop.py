from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from core.agent_approval import record_headless_approval_block
from core.agent_runtime_config import agent_max_steps
from core.agent_tool_events import parse_tool_arguments
from core.safety_policy import explain_policy_decision
from core.tool_execution_policy import (
    ToolExecutionGate,
    evaluate_tool_execution_gate,
    execute_with_runtime_policy,
)
from core.tool_registry import tool_policy_metadata


StreamExecutor = Callable[[str, list[dict], str, Any], AsyncIterator[dict]]


def _parse_headless_tool_call(tc: dict) -> tuple[str, dict]:
    func_name = tc.get("function", {}).get("name", "")
    try:
        func_args = parse_tool_arguments(
            tc.get("function", {}).get("arguments", "{}")
        )
    except Exception:
        func_args = {}
    return func_name, func_args


def _headless_high_risk_action_reason(tool_name: str, args: dict, context: dict) -> str:
    policy = explain_policy_decision(tool_name, args, context)
    if policy.get("decision") != "allow":
        return ""

    primary_action = policy.get("primary_action") or {}
    if primary_action.get("severity") not in {"high", "critical"}:
        return ""

    label = primary_action.get("label") or primary_action.get("id") or "高风险动作"
    return f"后台无人值守任务不自动执行高风险动作：{label}"


def _headless_execution_gate(
    *,
    tool_name: str,
    args: dict,
    context: dict,
    dispatcher: Any,
    tool_policy: dict[str, Any],
) -> ToolExecutionGate:
    check_gate = getattr(dispatcher, "check_execution_gate", None)
    if callable(check_gate):
        try:
            gate = check_gate(tool_name, args, context, policy=tool_policy)
        except TypeError:
            gate = check_gate(tool_name, args, context)
    else:
        needs_approval, reason = dispatcher.check_approval_needed(
            tool_name,
            args,
            context,
        )
        gate = evaluate_tool_execution_gate(
            tool_name,
            safety_needs_approval=needs_approval,
            safety_reason=reason,
            policy=tool_policy,
        )
    if gate.approval_required:
        return gate

    high_risk_reason = _headless_high_risk_action_reason(tool_name, args, context)
    if not high_risk_reason:
        return gate
    return ToolExecutionGate(
        True,
        high_risk_reason,
        gate.policy,
        ("safety_policy",),
    )


def _headless_approval_reason(
    *,
    tool_name: str,
    args: dict,
    context: dict,
    dispatcher: Any,
    tool_policy: dict[str, Any],
) -> str:
    return _headless_execution_gate(
        tool_name=tool_name,
        args=args,
        context=context,
        dispatcher=dispatcher,
        tool_policy=tool_policy,
    ).reason


def _build_headless_concurrent_plan(
    tool_calls: list[dict],
    *,
    dispatcher: Any,
    context: dict,
) -> list[dict[str, Any]] | None:
    if len(tool_calls) < 2:
        return None

    plan: list[dict[str, Any]] = []
    for tc in tool_calls:
        func_name, func_args = _parse_headless_tool_call(tc)
        tool_policy = tool_policy_metadata(func_name)
        if not tool_policy.get("concurrency_safe"):
            return None
        if _headless_execution_gate(
            tool_name=func_name,
            args=func_args,
            context=context,
            dispatcher=dispatcher,
            tool_policy=tool_policy,
        ).approval_required:
            return None
        plan.append(
            {
                "id": tc.get("id", ""),
                "name": func_name,
                "args": func_args,
                "policy": tool_policy,
            }
        )
    return plan


async def _run_headless_concurrent_plan(
    plan: list[dict[str, Any]],
    *,
    messages: list[dict],
    dispatcher: Any,
    context: dict,
) -> None:
    async def run_tool(item: dict[str, Any]) -> Any:
        return await execute_with_runtime_policy(
            item["name"],
            lambda: dispatcher.route_and_execute(
                item["name"],
                item["args"],
                context,
            ),
            policy=item["policy"],
        )

    results = await asyncio.gather(*(run_tool(item) for item in plan))
    for item, tool_res in zip(plan, results):
        messages.append(
            {
                "tool_call_id": item["id"],
                "role": "tool",
                "name": item["name"],
                "content": str(tool_res),
            }
        )


async def run_headless_agent_loop(
    *,
    model_name: str,
    messages: list[dict],
    tools: list[dict] | None,
    context: dict,
    session_id: str,
    agent_profile: str,
    host: str,
    dispatcher: Any,
    event_logger: logging.Logger,
    stream_executor: StreamExecutor | None = None,
    max_steps: int | None = None,
) -> str:
    if stream_executor is None:
        from core.llm_execution import execute_chat_stream

        stream_executor = execute_chat_stream

    assistant_content = ""
    step_limit = max_steps if max_steps is not None else agent_max_steps("headless")
    for _iteration in range(step_limit):
        assistant_content = ""
        thinking_content = ""
        tool_calls = []

        async for chunk in stream_executor(model_name, messages, "off", tools=tools):
            if chunk["type"] == "thinking":
                thinking_content += chunk["content"]
            elif chunk["type"] == "content":
                assistant_content += chunk["content"]
            elif chunk["type"] == "tool_calls":
                tool_calls = chunk["tool_calls"]

        if not tool_calls:
            break

        safe_msg = {"role": "assistant", "content": assistant_content}
        if thinking_content:
            safe_msg["reasoning_content"] = thinking_content
        safe_msg["tool_calls"] = tool_calls

        messages.append(safe_msg)

        concurrent_plan = _build_headless_concurrent_plan(
            tool_calls,
            dispatcher=dispatcher,
            context=context,
        )
        if concurrent_plan:
            await _run_headless_concurrent_plan(
                concurrent_plan,
                messages=messages,
                dispatcher=dispatcher,
                context=context,
            )
            continue

        for tc in tool_calls:
            func_name, func_args = _parse_headless_tool_call(tc)
            tool_policy = tool_policy_metadata(func_name)
            reason = _headless_approval_reason(
                tool_name=func_name,
                args=func_args,
                context=context,
                dispatcher=dispatcher,
                tool_policy=tool_policy,
            )

            if reason:
                blocked = record_headless_approval_block(
                    tool_call_id=tc.get("id", ""),
                    session_id=session_id,
                    tool_name=func_name,
                    args=func_args,
                    reason=reason,
                    context=context,
                )
                event_logger.warning(
                    "Blocked unattended tool call requiring approval: session=%s tool=%s approval=%s",
                    session_id,
                    func_name,
                    blocked.get("id"),
                )
                tool_res = json.dumps(
                    {
                        "status": "BLOCKED",
                        "error": f"后台自治任务触发审批策略，已自动阻断: {reason}",
                        "approval_id": blocked.get("id"),
                    },
                    ensure_ascii=False,
                )
            else:
                tool_res = await execute_with_runtime_policy(
                    func_name,
                    lambda: dispatcher.route_and_execute(
                        func_name,
                        func_args,
                        context,
                    ),
                    policy=tool_policy,
                )

            tool_msg = {
                "tool_call_id": tc.get("id", ""),
                "role": "tool",
                "name": func_name,
                "content": str(tool_res),
            }
            messages.append(tool_msg)
    else:
        return (
            f"任务达到 {step_limit} 步执行保护上限，系统已停止继续调用工具。以下是最后一轮阶段性结果："
            + assistant_content
        )

    return f"来自 {agent_profile} Agent ({host}) 的协同任务报告：\n" + assistant_content
