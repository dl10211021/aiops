from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from core.agent_approval import record_headless_approval_block
from core.agent_runtime_config import agent_max_steps
from core.agent_tool_events import parse_tool_arguments


StreamExecutor = Callable[[str, list[dict], str, Any], AsyncIterator[dict]]


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

        for tc in tool_calls:
            func_name = tc.get("function", {}).get("name", "")
            try:
                func_args = parse_tool_arguments(
                    tc.get("function", {}).get("arguments", "{}")
                )
            except Exception:
                func_args = {}

            needs_approval, reason = dispatcher.check_approval_needed(
                func_name,
                func_args,
                context,
            )
            if needs_approval:
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
                tool_res = await dispatcher.route_and_execute(
                    func_name,
                    func_args,
                    context,
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
