from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol

from core.agent_runtime_config import agent_step_limit_instruction
from core.agent_sse import sse_event
from core.tool_trace_policy import trace_evidence_id, trace_policy_summary


class StepSummaryMemoryStore(Protocol):
    def append_message(self, session_id: str, message: dict) -> None:
        ...


StepSummaryExecutor = Callable[
    [str, list[dict], str, object | None],
    AsyncIterator[dict],
]


async def _default_step_summary_executor(
    model_name: str,
    messages: list[dict],
    thinking_mode: str,
    tools: object | None = None,
) -> AsyncIterator[dict]:
    from core.llm_execution import execute_chat_stream

    async for chunk in execute_chat_stream(model_name, messages, thinking_mode, tools=tools):
        yield chunk


def _step_summary_audit_message(exec_trace: list[dict] | None) -> dict | None:
    if not exec_trace:
        return None
    lines: list[str] = []
    for index, trace in enumerate(exec_trace[-12:], start=1):
        if not isinstance(trace, dict):
            continue
        lines.append(
            f"{index}. tool={trace.get('tool') or 'unknown'}; "
            f"status={trace.get('status') or 'done'}; "
            f"policy={trace_policy_summary(trace) or '-'}; "
            f"evidence={trace_evidence_id(trace) or '-'}; "
            f"execute={str(trace.get('args') or '-')[:500]}; "
            f"result={str(trace.get('result') or '-')[:900]}"
        )
    if not lines:
        return None
    return {
        "role": "system",
        "content": (
            "[工具审计上下文]\n"
            "下面是本轮达到步数上限前已经完成的工具轨迹。阶段性报告必须基于这些真实证据，"
            "并保留策略、证据编号和失败/阻断状态；不要继续调用工具。\n"
            + "\n".join(lines)
        ),
    }


async def stream_step_limit_summary(
    *,
    model_name: str,
    messages: list[dict],
    session_id: str,
    max_steps: int,
    memory_store: StepSummaryMemoryStore,
    exec_trace: list[dict] | None = None,
    stream_executor: StepSummaryExecutor | None = None,
) -> AsyncIterator[str]:
    yield sse_event(
        {
            "type": "status",
            "content": f"已达到 {max_steps} 步执行保护上限，正在整理阶段性报告...",
        },
        ensure_ascii=False,
    )

    executor = stream_executor or _default_step_summary_executor
    audit_message = _step_summary_audit_message(exec_trace)
    summary_messages = list(messages)
    if audit_message:
        summary_messages.append(audit_message)
    summary_messages.append(
        {"role": "system", "content": agent_step_limit_instruction(max_steps)}
    )
    summary_content = ""

    try:
        async for chunk in executor(model_name, summary_messages, "off", None):
            if chunk["type"] == "content":
                summary_content += chunk["content"]
                yield sse_event(
                    {"type": "chunk", "content": chunk["content"]},
                    ensure_ascii=False,
                )
            elif chunk["type"] == "thinking":
                continue
        if not summary_content.strip():
            summary_content = (
                f"已达到 {max_steps} 步执行保护上限，系统已停止继续调用工具。"
                "当前模型未能生成阶段性报告，请根据上方工具结果继续拆分任务。"
            )
            yield sse_event(
                {"type": "chunk", "content": summary_content},
                ensure_ascii=False,
            )
    except Exception as summary_error:
        summary_content = (
            f"已达到 {max_steps} 步执行保护上限，且阶段性报告生成失败：{summary_error}。"
            "请将任务拆成更小范围后重试。"
        )
        yield sse_event(
            {"type": "chunk", "content": summary_content},
            ensure_ascii=False,
        )

    safe_summary_msg = {"role": "assistant", "content": summary_content}
    messages.append(safe_summary_msg)
    memory_store.append_message(session_id, safe_summary_msg)
    yield sse_event({"type": "done"})
