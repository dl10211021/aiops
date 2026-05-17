from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from core.agent_approval import record_headless_approval_block
from core.agent_runtime_config import agent_max_steps
from core.agent_tool_events import _session_mode_from_context, parse_tool_arguments, summarize_tool_result_for_sse
from core.run_hooks import emit_run_hook
from core.safety_policy import explain_policy_decision
from core.tool_evidence import build_tool_evidence
from core.tool_execution_policy import (
    ToolExecutionGate,
    evaluate_tool_execution_gate,
    execute_with_runtime_policy,
)
from core.tool_registry import tool_policy_metadata
from core.tool_trace_policy import trace_command_actions, trace_command_primary_action


StreamExecutor = Callable[[str, list[dict], str, Any], AsyncIterator[dict]]


def _headless_hook_context(context: dict) -> dict[str, Any]:
    keys = (
        "session_id",
        "execution_mode",
        "session_mode",
        "mode",
        "asset_id",
        "asset_type",
        "protocol",
        "host",
        "port",
        "allow_modifications",
        "prompt_modules",
        "observability_task_id",
        "investigation_id",
    )
    return {key: context.get(key) for key in keys if key in context}


async def _emit_headless_run_hook(
    emitter: Callable[[str, dict[str, Any]], Awaitable[None]],
    event_type: str,
    payload: dict[str, Any],
    event_logger: logging.Logger,
) -> None:
    try:
        await emitter(event_type, payload)
    except Exception as exc:
        event_logger.warning("Headless run hook failed for %s: %s", event_type, exc)


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
    async def run_tool(item: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        runtime_execution: dict[str, Any] = {}
        tool_res = await execute_with_runtime_policy(
            item["name"],
            lambda: dispatcher.route_and_execute(
                item["name"],
                item["args"],
                context,
            ),
            policy=item["policy"],
            runtime_stats=runtime_execution,
        )
        runtime_execution["concurrent"] = True
        return tool_res, runtime_execution

    results = await asyncio.gather(*(run_tool(item) for item in plan))
    for item, result in zip(plan, results):
        tool_res, runtime_execution = result
        messages.append(
            {
                "tool_call_id": item["id"],
                "role": "tool",
                "name": item["name"],
                "content": _headless_tool_message_content(
                    tool_res,
                    item["name"],
                    item["args"],
                    item["policy"],
                    runtime_execution,
                    context,
                ),
            }
        )


def _headless_tool_message_content(
    tool_res: Any,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_policy: dict[str, Any],
    runtime_execution: dict[str, Any] | None,
    context: dict,
) -> str:
    if isinstance(tool_res, dict):
        payload = dict(tool_res)
    elif isinstance(tool_res, str):
        try:
            parsed = json.loads(tool_res)
        except Exception:
            parsed = None
        payload = parsed if isinstance(parsed, dict) else {"result": tool_res}
    else:
        payload = {"result": tool_res}

    payload.setdefault("tool", tool_name)
    payload.setdefault("tool_policy", tool_policy)
    trace = {"tool": tool_name, "args": tool_args, "resultMeta": payload}
    primary_action = trace_command_primary_action(trace)
    if primary_action:
        payload.setdefault("primary_action", primary_action)
        actions = trace_command_actions(trace)
        if actions:
            payload.setdefault("actions", actions)
    if runtime_execution:
        payload.setdefault("runtime_policy", runtime_execution)
    session_mode = _session_mode_from_context(context)
    if session_mode:
        payload.setdefault("session_mode", session_mode)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _headless_tool_evidence(
    *,
    tool_call_id: str,
    session_id: str,
    context: dict,
    tool_name: str,
    args: dict[str, Any],
    tool_result: Any,
    result_meta: dict[str, Any],
    started_at: int | None,
    finished_at: int | None,
    approval_ref: str | None = None,
) -> dict[str, Any]:
    summary = summarize_tool_result_for_sse(tool_result)
    evidence = build_tool_evidence(
        tool_call_id=tool_call_id,
        session_id=session_id,
        context=context,
        tool_name=tool_name,
        input_summary=json.dumps(args, ensure_ascii=False, default=str),
        output_preview=summary["preview"],
        result_status=summary["status"],
        result_meta=result_meta,
        started_at=started_at,
        finished_at=finished_at,
        approval_ref=approval_ref,
    )
    for key in ("observability_task_id", "investigation_id"):
        value = str(context.get(key) or "").strip()
        if value:
            evidence[key] = value[:120]
    return evidence


async def _emit_headless_tool_hook(
    emitter: Callable[[str, dict[str, Any]], Awaitable[None]],
    event_type: str,
    payload: dict[str, Any],
    event_logger: logging.Logger,
) -> None:
    try:
        await emitter(event_type, payload)
    except Exception as exc:
        event_logger.warning("Headless tool hook failed for %s: %s", event_type, exc)


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
    run_hook_emitter: Callable[[str, dict[str, Any]], Awaitable[None]] = emit_run_hook,
) -> str:
    if stream_executor is None:
        from core.llm_execution import execute_chat_stream

        stream_executor = execute_chat_stream

    assistant_content = ""
    step_limit = max_steps if max_steps is not None else agent_max_steps("headless")
    run_status = "completed"
    run_reason = "completed"
    await _emit_headless_run_hook(
        run_hook_emitter,
        "run:start",
        {
            "session_id": session_id,
            "model_name": model_name,
            "agent_profile": agent_profile,
            "host": host,
            "max_steps": step_limit,
            "context": _headless_hook_context(context),
        },
        event_logger,
    )
    try:
        for iteration in range(step_limit):
            await _emit_headless_run_hook(
                run_hook_emitter,
                "agent:step",
                {
                    "session_id": session_id,
                    "iteration": iteration,
                    "max_steps": step_limit,
                    "model_name": model_name,
                    "agent_profile": agent_profile,
                    "host": host,
                    "context": _headless_hook_context(context),
                },
                event_logger,
            )
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
                tool_call_id = str(tc.get("id") or "")
                tool_policy = tool_policy_metadata(func_name)
                started_at = int(time.time() * 1000)
                await _emit_headless_tool_hook(
                    run_hook_emitter,
                    "tool:before",
                    {
                        "session_id": session_id,
                        "tool_call_id": tool_call_id,
                        "tool_name": func_name,
                        "args": func_args,
                        "iteration": iteration,
                        "context": _headless_hook_context(context),
                        "tool_policy": tool_policy,
                        "started_at": started_at,
                    },
                    event_logger,
                )
                gate = _headless_execution_gate(
                    tool_name=func_name,
                    args=func_args,
                    context=context,
                    dispatcher=dispatcher,
                    tool_policy=tool_policy,
                )
                reason = gate.reason
                approval_sources = gate.approval_sources

                if reason:
                    blocked = record_headless_approval_block(
                        tool_call_id=tc.get("id", ""),
                        session_id=session_id,
                        tool_name=func_name,
                        args=func_args,
                        reason=reason,
                        context=context,
                        approval_sources=approval_sources,
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
                    runtime_execution = {}
                    tool_res = await execute_with_runtime_policy(
                        func_name,
                        lambda: dispatcher.route_and_execute(
                            func_name,
                            func_args,
                            context,
                        ),
                        policy=tool_policy,
                        runtime_stats=runtime_execution,
                    )

                finished_at = int(time.time() * 1000)
                result_meta = {}
                tool_msg = {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": func_name,
                    "content": _headless_tool_message_content(
                        tool_res,
                        func_name,
                        func_args,
                        tool_policy,
                        runtime_execution if not reason else {},
                        context,
                    ),
                }
                try:
                    parsed_tool_payload = json.loads(tool_msg["content"])
                except Exception:
                    parsed_tool_payload = {}
                if isinstance(parsed_tool_payload, dict):
                    result_meta = {
                        key: parsed_tool_payload[key]
                        for key in (
                            "tool_policy",
                            "runtime_policy",
                            "session_mode",
                            "primary_action",
                            "actions",
                            "approval_id",
                        )
                        if key in parsed_tool_payload
                    }
                evidence = _headless_tool_evidence(
                    tool_call_id=tool_call_id,
                    session_id=session_id,
                    context=context,
                    tool_name=func_name,
                    args=func_args,
                    tool_result=tool_res,
                    result_meta=result_meta,
                    started_at=started_at,
                    finished_at=finished_at,
                    approval_ref=str(parsed_tool_payload.get("approval_id") or "") if isinstance(parsed_tool_payload, dict) else "",
                )
                await _emit_headless_tool_hook(
                    run_hook_emitter,
                    "tool:after",
                    {
                        "session_id": session_id,
                        "tool_call_id": tool_call_id,
                        "tool_name": func_name,
                        "args": func_args,
                        "iteration": iteration,
                        "context": _headless_hook_context(context),
                        "status": evidence.get("result_status") or "done",
                        "result_meta": result_meta,
                        "evidence_id": evidence.get("evidence_id") or "",
                        "evidence": evidence,
                        "started_at": started_at,
                        "finished_at": finished_at,
                    },
                    event_logger,
                )
                messages.append(tool_msg)
        else:
            run_reason = "step_limit"
            return (
                f"任务达到 {step_limit} 步执行保护上限，系统已停止继续调用工具。以下是最后一轮阶段性结果："
                + assistant_content
            )

        return f"来自 {agent_profile} Agent ({host}) 的协同任务报告：\n" + assistant_content
    except Exception:
        run_status = "failed"
        run_reason = "exception"
        raise
    finally:
        await _emit_headless_run_hook(
            run_hook_emitter,
            "run:end",
            {
                "session_id": session_id,
                "model_name": model_name,
                "agent_profile": agent_profile,
                "host": host,
                "status": run_status,
                "reason": run_reason,
                "context": _headless_hook_context(context),
            },
            event_logger,
        )
