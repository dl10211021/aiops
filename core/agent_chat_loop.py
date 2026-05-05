from __future__ import annotations

import asyncio
import time
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

from core.agent_ltm import schedule_ltm_compression
from core.agent_runtime_config import agent_max_steps
from core.agent_sse import sse_event
from core.agent_step_summary import stream_step_limit_summary
from core.agent_streaming import AgentStreamState, stream_assistant_response
from core.agent_tool_loop import process_chat_tool_calls
from core.assistant_model_config import (
    assistant_task_enabled,
    assistant_thinking_mode,
    get_assistant_model_config,
    resolve_assistant_model_id,
)


class ChatLoopMemoryStore(Protocol):
    def append_message(self, session_id: str, message: dict) -> int | None:
        ...

    def update_message_exec_trace(
        self,
        session_id: str,
        message_id: int,
        exec_trace: list[dict],
    ) -> None:
        ...

    async def compress_and_store_ltm(
        self,
        session_id: str,
        emb_client: Any,
        embedding_model: str,
    ) -> None:
        ...


async def run_chat_agent_loop(
    *,
    session_id: str,
    model_name: str,
    thinking_mode: str,
    orchestration_mode: str = "single",
    messages: list[dict],
    context: dict,
    tools: list[dict],
    memory_store: ChatLoopMemoryStore,
    dispatcher: Any,
    cancel_flags: dict[str, bool],
    emb_client: Any,
    embedding_model: str,
    memory_references: list[dict[str, Any]] | None = None,
    event_logger: logging.Logger,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    max_steps_resolver: Callable[[str], int] = agent_max_steps,
    assistant_streamer: Callable[..., AsyncIterator[str]] = stream_assistant_response,
    tool_call_processor: Callable[..., AsyncIterator[str]] = process_chat_tool_calls,
    step_summary_streamer: Callable[..., AsyncIterator[str]] = stream_step_limit_summary,
    compression_scheduler: Callable[..., Any] = schedule_ltm_compression,
) -> AsyncIterator[str]:
    yield sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."})
    await sleep(0.05)

    orchestration = _resolve_model_orchestration(model_name, orchestration_mode)
    if orchestration["enabled"]:
        async for event in _run_split_model_chat_agent_loop(
            session_id=session_id,
            model_name=model_name,
            thinking_mode=thinking_mode,
            messages=messages,
            context=context,
            tools=tools,
            memory_store=memory_store,
            dispatcher=dispatcher,
            cancel_flags=cancel_flags,
            event_logger=event_logger,
            sleep=sleep,
            max_steps=max_steps_resolver("chat"),
            tool_call_processor=tool_call_processor,
            step_summary_streamer=step_summary_streamer,
            orchestration=orchestration,
            memory_references=memory_references,
        ):
            yield event
        compression_scheduler(
            memory_store=memory_store,
            session_id=session_id,
            emb_client=emb_client,
            embedding_model=embedding_model,
            primary_model_id=model_name,
            memory_scope_ids=context.get("memory_scope_ids"),
        )
        return

    max_steps = max_steps_resolver("chat")
    pending_memory_references = list(memory_references or [])
    for iteration in range(max_steps):
        event_logger.info(
            f"Loop {iteration} for {session_id}, cancel_flags: {cancel_flags.get(session_id)}"
        )
        if cancel_flags.get(session_id) is True:
            cancel_flags[session_id] = False
            yield sse_event({"type": "error", "content": "任务已被手动中止。"})
            yield sse_event({"type": "done"})
            break

        yield sse_event({"type": "status", "content": "💭 思考中..."})

        stream_state = AgentStreamState()
        async for event in assistant_streamer(
            model_name=model_name,
            messages=messages,
            thinking_mode=thinking_mode,
            tools=tools,
            state=stream_state,
            cancel_requested=lambda: cancel_flags.get(session_id) is True,
        ):
            yield event

        tool_calls = stream_state.tool_calls
        safe_msg = stream_state.assistant_message()
        if not tool_calls:
            pending_memory_references = _attach_memory_references_if_visible(
                safe_msg,
                pending_memory_references,
            )
        messages.append(safe_msg)
        assistant_memory_id = memory_store.append_message(session_id, safe_msg)

        if not tool_calls:
            memory_ref_event = _memory_references_sse_event(safe_msg)
            if memory_ref_event:
                yield memory_ref_event
            yield sse_event({"type": "done"})
            break

        exec_trace: list[dict] = []

        def record_exec_trace(event: dict) -> None:
            event_type = event.get("type")
            now_ms = int(time.time() * 1000)
            if event_type == "tool_start":
                exec_trace.append(
                    {
                        "type": "tool_start",
                        "tool": str(event.get("tool") or "unknown"),
                        "args": str(event.get("args") or ""),
                        "status": "running",
                        "startedAt": now_ms,
                    }
                )
                return
            if event_type != "tool_end":
                return
            completed = {
                "type": "tool_end",
                "tool": str(event.get("tool") or "unknown"),
                "result": str(event.get("result") or ""),
                "resultMeta": event.get("resultMeta") or {},
                "status": event.get("status") if event.get("status") in {"done", "error"} else "done",
                "completedAt": now_ms,
            }
            for index in range(len(exec_trace) - 1, -1, -1):
                item = exec_trace[index]
                if item.get("type") == "tool_start" and item.get("status") == "running":
                    exec_trace[index] = {**item, **completed}
                    return
            exec_trace.append(completed)

        async for event in tool_call_processor(
            tool_calls=tool_calls,
            session_id=session_id,
            messages=messages,
            memory_store=memory_store,
            dispatcher=dispatcher,
            context=context,
            iteration=iteration,
            trace_collector=record_exec_trace,
        ):
            yield event
        if assistant_memory_id and exec_trace:
            if assistant_task_enabled("trace_review") or assistant_task_enabled("risk_advice"):
                yield sse_event({"type": "status", "content": "🧩 正在审查本轮思维链和风险建议..."})
                await append_assistant_trace_review(
                    model_name=resolve_assistant_model_id(model_name),
                    thinking_mode=assistant_thinking_mode(),
                    messages=messages,
                    context=context,
                    exec_trace=exec_trace,
                    assistant_content=safe_msg.get("content") or "",
                    event_logger=event_logger,
                )
            memory_store.update_message_exec_trace(
                session_id,
                assistant_memory_id,
                exec_trace,
            )
            success_memory = build_successful_execution_memory(
                session_id=session_id,
                context=context,
                exec_trace=exec_trace,
                assistant_content=safe_msg.get("content") or "",
            )
            if success_memory:
                memory_store.append_message(session_id, success_memory)

    else:
        async for event in step_summary_streamer(
            model_name=model_name,
            messages=messages,
            session_id=session_id,
            max_steps=max_steps,
            memory_store=memory_store,
        ):
            yield event

    compression_scheduler(
        memory_store=memory_store,
        session_id=session_id,
        emb_client=emb_client,
        embedding_model=embedding_model,
        primary_model_id=model_name,
        memory_scope_ids=context.get("memory_scope_ids"),
    )


def _resolve_model_orchestration(primary_model_id: str, orchestration_mode: str = "single") -> dict[str, Any]:
    config = get_assistant_model_config()
    assistant_model_id = resolve_assistant_model_id(primary_model_id)
    mode = orchestration_mode if orchestration_mode in {"single", "split", "auto"} else "single"
    assistant_configured = bool(config.get("enabled") and config.get("model_id"))
    assistant_delegated = bool(assistant_configured and assistant_model_id != primary_model_id)
    enabled = mode == "split" or (mode == "auto" and assistant_configured)
    return {
        "enabled": enabled,
        "mode": mode,
        "primary_model_id": primary_model_id,
        "assistant_model_id": assistant_model_id,
        "assistant_delegated": assistant_delegated,
        "assistant_thinking_mode": assistant_thinking_mode(),
        "completion_check": assistant_task_enabled("completion_check"),
        "trace_review": assistant_task_enabled("trace_review"),
        "risk_advice": assistant_task_enabled("risk_advice"),
    }


def _assistant_orchestration_labels(orchestration: dict[str, Any]) -> dict[str, str]:
    assistant_model_id = str(orchestration.get("assistant_model_id") or orchestration.get("primary_model_id") or "")
    if orchestration.get("assistant_delegated"):
        return {
            "intent": f"🧭 主模型正在决定执行目标，辅助模型随后负责选择工具：{assistant_model_id}",
            "tool": "🧠 辅助模型正在选择工具和下一步动作...",
            "final": "📝 辅助模型正在整理最终回复...",
        }
    return {
        "intent": f"🧭 主模型正在决定执行目标，并接管辅助模型职责：{assistant_model_id}",
        "tool": "🧠 主模型正在接管工具选择和下一步动作...",
        "final": "📝 主模型正在整理最终回复...",
    }


async def _collect_model_turn(
    *,
    model_name: str,
    messages: list[dict],
    thinking_mode: str,
    tools: list[dict] | None = None,
) -> AgentStreamState:
    from core.llm_execution import execute_chat_stream

    state = AgentStreamState()
    async for chunk in execute_chat_stream(
        model_name,
        messages,
        thinking_mode,
        tools=tools,
    ):
        if chunk["type"] == "thinking":
            state.thinking_content += chunk["content"]
        elif chunk["type"] == "content":
            state.assistant_content += chunk["content"]
        elif chunk["type"] == "tool_calls":
            state.tool_calls = chunk["tool_calls"]
    return state


async def _collect_model_text(
    *,
    model_name: str,
    messages: list[dict],
    thinking_mode: str,
) -> str:
    state = await _collect_model_turn(
        model_name=model_name,
        messages=messages,
        thinking_mode=thinking_mode,
        tools=None,
    )
    return (state.assistant_content or "").strip()


def _split_text_for_sse(text: str, chunk_size: int = 800) -> list[str]:
    if not text:
        return []
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]


def _build_execution_intent_prompt(context: dict) -> str:
    return f"""
你是 OpsCore 的主模型，负责决定本轮会话“要做什么”和安全边界，但不要选择具体工具。
请基于当前资产和用户请求，输出一段不超过 220 字的执行意图，包含：
1. 本轮目标；
2. 必须遵守的边界；
3. 工具选择时应优先考虑的证据方向。

当前资产：{context.get('asset_type')}/{context.get('protocol')} {context.get('host')}:{context.get('port')}
当前模式：{'允许变更但需遵守审批策略' if context.get('allow_modifications') else '只读优先，禁止主动变更'}
只输出执行意图，不要输出最终报告。
""".strip()


def _build_final_writer_prompt(context: dict) -> str:
    return f"""
你是 OpsCore 的辅助思维模型，负责把本轮会话的用户问题、工具执行结果和证据整理成最终中文回复。
要求：
1. 必须基于真实工具结果，不要编造未采集数据；
2. 把结论、关键证据、风险等级、建议动作写清楚；
3. 多轮工具调用要按逻辑合并，不要只复述 JSON；
4. 如果工具被阻止或失败，要说明失败原因和下一步可选动作；
5. 输出给用户可直接阅读的最终回复，不要再要求调用工具。

当前资产：{context.get('asset_type')}/{context.get('protocol')} {context.get('host')}:{context.get('port')}
""".strip()


def _build_final_review_prompt(context: dict, draft: str) -> str:
    return f"""
你是 OpsCore 的主模型，负责审核辅助模型写出的最终回复并做兜底。
请检查回复是否：
1. 只基于真实工具结果；
2. 没有危险命令误导；
3. 没有遗漏明显失败/阻断/风险；
4. 中文表达清晰。

如果没有问题，请原样返回最终回复。
如果有问题，请直接返回修正后的最终回复。
不要输出审查过程，不要输出 JSON，不要输出“审核通过”等额外说明。

当前资产：{context.get('asset_type')}/{context.get('protocol')} {context.get('host')}:{context.get('port')}

待审核回复：
{draft}
""".strip()


def _build_trace_review_prompt(
    context: dict,
    exec_trace: list[dict],
    assistant_content: str,
    *,
    want_trace_review: bool,
    want_risk_advice: bool,
) -> str:
    trace_lines = []
    for index, item in enumerate(exec_trace[-12:], start=1):
        trace_lines.append(
            "\n".join(
                [
                    f"{index}. 工具：{item.get('tool') or 'unknown'}",
                    f"状态：{item.get('status') or '-'}",
                    f"执行：{str(item.get('args') or '-')[:900]}",
                    f"结果：{str(item.get('result') or '-')[:1400]}",
                ]
            )
        )
    sections = []
    if want_trace_review:
        sections.append(
            "【思维链审查】用 3-6 条中文要点说明本轮工具执行是否完整、是否被策略阻止、是否存在采集盲区、哪些证据最关键。"
        )
    if want_risk_advice:
        sections.append(
            "【风险建议】用 P0/P1/P2 中文要点输出后续建议，只基于真实工具结果；没有证据时写“暂无明确风险证据”。"
        )
    return f"""
你是 OpsCore 的辅助审查模型。请对本轮工具执行轨迹做审查，输出给右侧思维链归档使用。
要求：
1. 只基于下面的工具执行结果和 AI 输出摘要，不要编造；
2. 如果发现工具被安全策略阻止，要明确写出阻止原因和下一步只读替代方案；
3. 输出必须包含要求的标题，不要输出 JSON。

当前资产：{context.get('asset_type')}/{context.get('protocol')} {context.get('host')}:{context.get('port')}
当前模式：{'可修改' if context.get('allow_modifications') else '只读'}

需要输出：
{chr(10).join(sections) or '无'}

工具执行轨迹：
{chr(10).join(trace_lines) or '-'}

AI 输出摘要：
{assistant_content[:1200] or '-'}
""".strip()


def _extract_review_section(text: str, title: str) -> str:
    marker = f"【{title}】"
    start = text.find(marker)
    if start < 0:
        return text.strip()
    start += len(marker)
    next_start = text.find("【", start)
    if next_start < 0:
        return text[start:].strip()
    return text[start:next_start].strip()


async def append_assistant_trace_review(
    *,
    model_name: str,
    thinking_mode: str,
    messages: list[dict],
    context: dict,
    exec_trace: list[dict],
    assistant_content: str,
    event_logger: logging.Logger,
) -> None:
    want_trace_review = assistant_task_enabled("trace_review")
    want_risk_advice = assistant_task_enabled("risk_advice")
    if not exec_trace or not (want_trace_review or want_risk_advice):
        return
    try:
        review_text = await _collect_model_text(
            model_name=model_name,
            messages=[
                *messages[-10:],
                {
                    "role": "system",
                    "content": _build_trace_review_prompt(
                        context,
                        exec_trace,
                        assistant_content,
                        want_trace_review=want_trace_review,
                        want_risk_advice=want_risk_advice,
                    ),
                },
            ],
            thinking_mode=thinking_mode,
        )
    except Exception as exc:
        event_logger.warning("Assistant trace review failed: %s", exc)
        return
    review_text = review_text.strip()
    if not review_text:
        return
    now_ms = int(time.time() * 1000)
    if want_trace_review:
        trace_review = _extract_review_section(review_text, "思维链审查")
        if trace_review:
            exec_trace.append(
                {
                    "type": "tool_end",
                    "tool": "思维链审查",
                    "args": "审查本轮工具执行轨迹、阻断、盲区和关键证据",
                    "result": trace_review,
                    "status": "done",
                    "completedAt": now_ms,
                }
            )
    if want_risk_advice:
        risk_advice = _extract_review_section(review_text, "风险建议")
        if risk_advice:
            exec_trace.append(
                {
                    "type": "tool_end",
                    "tool": "风险建议",
                    "args": "基于本轮真实证据生成 P0/P1/P2 后续建议",
                    "result": risk_advice,
                    "status": "done",
                    "completedAt": now_ms,
                }
            )


async def _run_split_model_chat_agent_loop(
    *,
    session_id: str,
    model_name: str,
    thinking_mode: str,
    messages: list[dict],
    context: dict,
    tools: list[dict],
    memory_store: ChatLoopMemoryStore,
    dispatcher: Any,
    cancel_flags: dict[str, bool],
    event_logger: logging.Logger,
    sleep: Callable[[float], Awaitable[None]],
    max_steps: int,
    tool_call_processor: Callable[..., AsyncIterator[str]],
    step_summary_streamer: Callable[..., AsyncIterator[str]],
    orchestration: dict[str, Any],
    memory_references: list[dict[str, Any]] | None = None,
) -> AsyncIterator[str]:
    primary_model_id = str(orchestration["primary_model_id"])
    assistant_model_id = str(orchestration["assistant_model_id"] or model_name)
    assistant_mode = str(orchestration.get("assistant_thinking_mode") or "high")
    pending_memory_references = list(memory_references or [])
    labels = _assistant_orchestration_labels(orchestration)

    yield sse_event(
        {
            "type": "status",
            "content": labels["intent"],
        }
    )
    intent_text = ""
    try:
        intent_text = await _collect_model_text(
            model_name=primary_model_id,
            messages=[
                *messages,
                {"role": "system", "content": _build_execution_intent_prompt(context)},
            ],
            thinking_mode=thinking_mode,
        )
    except Exception as exc:
        event_logger.warning("Primary model intent planning failed: %s", exc)

    if intent_text:
        messages.append(
            {
                "role": "system",
                "content": f"【主模型执行意图】\n{intent_text}",
            }
        )

    for iteration in range(max_steps):
        event_logger.info(
            "Split model loop %s for %s, cancel_flags: %s",
            iteration,
            session_id,
            cancel_flags.get(session_id),
        )
        if cancel_flags.get(session_id) is True:
            cancel_flags[session_id] = False
            yield sse_event({"type": "error", "content": "任务已被手动中止。"})
            yield sse_event({"type": "done"})
            return

        yield sse_event({"type": "status", "content": labels["tool"]})

        try:
            stream_state = await _collect_model_turn(
                model_name=assistant_model_id,
                messages=messages,
                thinking_mode=assistant_mode,
                tools=tools,
            )
        except Exception as exc:
            event_logger.warning("Assistant tool planning failed, falling back to primary model: %s", exc)
            stream_state = await _collect_model_turn(
                model_name=primary_model_id,
                messages=messages,
                thinking_mode=thinking_mode,
                tools=tools,
            )

        tool_calls = stream_state.tool_calls
        safe_msg = stream_state.assistant_message()

        if not tool_calls:
            draft_messages = [
                *messages,
                safe_msg,
                {"role": "system", "content": _build_final_writer_prompt(context)},
            ]
            yield sse_event({"type": "status", "content": labels["final"]})
            try:
                final_text = await _collect_model_text(
                    model_name=assistant_model_id,
                    messages=draft_messages,
                    thinking_mode=assistant_mode,
                )
            except Exception as exc:
                event_logger.warning("Assistant final writer failed, using planner text: %s", exc)
                final_text = str(safe_msg.get("content") or "").strip()

            if orchestration.get("completion_check"):
                yield sse_event({"type": "status", "content": "🛡️ 主模型正在审核最终回复..."})
                try:
                    reviewed_text = await _collect_model_text(
                        model_name=primary_model_id,
                        messages=[
                            *messages,
                            {"role": "assistant", "content": final_text},
                            {"role": "system", "content": _build_final_review_prompt(context, final_text)},
                        ],
                        thinking_mode=thinking_mode,
                    )
                    if reviewed_text:
                        final_text = reviewed_text
                except Exception as exc:
                    event_logger.warning("Primary model final review failed, keeping assistant final: %s", exc)

            final_msg = {"role": "assistant", "content": final_text}
            pending_memory_references = _attach_memory_references_if_visible(
                final_msg,
                pending_memory_references,
            )
            messages.append(final_msg)
            memory_store.append_message(session_id, final_msg)
            for chunk in _split_text_for_sse(final_text):
                yield sse_event({"type": "chunk", "content": chunk})
                await sleep(0.01)
            memory_ref_event = _memory_references_sse_event(final_msg)
            if memory_ref_event:
                yield memory_ref_event
            yield sse_event({"type": "done"})
            return

        # Keep memory/RAG references pending while the model is still calling tools.
        # The user should see those references on the final answer, not on an
        # intermediate planning message.
        messages.append(safe_msg)
        assistant_memory_id = memory_store.append_message(session_id, safe_msg)
        exec_trace: list[dict] = []

        def record_exec_trace(event: dict) -> None:
            event_type = event.get("type")
            now_ms = int(time.time() * 1000)
            if event_type == "tool_start":
                exec_trace.append(
                    {
                        "type": "tool_start",
                        "tool": str(event.get("tool") or "unknown"),
                        "args": str(event.get("args") or ""),
                        "status": "running",
                        "startedAt": now_ms,
                    }
                )
                return
            if event_type != "tool_end":
                return
            completed = {
                "type": "tool_end",
                "tool": str(event.get("tool") or "unknown"),
                "result": str(event.get("result") or ""),
                "resultMeta": event.get("resultMeta") or {},
                "status": event.get("status") if event.get("status") in {"done", "error"} else "done",
                "completedAt": now_ms,
            }
            for index in range(len(exec_trace) - 1, -1, -1):
                item = exec_trace[index]
                if item.get("type") == "tool_start" and item.get("status") == "running":
                    exec_trace[index] = {**item, **completed}
                    return
            exec_trace.append(completed)

        yield sse_event({"type": "status", "content": "⚙️ 主流程正在执行工具调用并记录证据..."})
        async for event in tool_call_processor(
            tool_calls=tool_calls,
            session_id=session_id,
            messages=messages,
            memory_store=memory_store,
            dispatcher=dispatcher,
            context=context,
            iteration=iteration,
            trace_collector=record_exec_trace,
        ):
            yield event

        if assistant_memory_id and exec_trace:
            if orchestration.get("trace_review") or orchestration.get("risk_advice"):
                yield sse_event({"type": "status", "content": "🧩 正在审查本轮思维链和风险建议..."})
                await append_assistant_trace_review(
                    model_name=assistant_model_id,
                    thinking_mode=assistant_mode,
                    messages=messages,
                    context=context,
                    exec_trace=exec_trace,
                    assistant_content=safe_msg.get("content") or "",
                    event_logger=event_logger,
                )
            memory_store.update_message_exec_trace(
                session_id,
                assistant_memory_id,
                exec_trace,
            )
            success_memory = build_successful_execution_memory(
                session_id=session_id,
                context=context,
                exec_trace=exec_trace,
                assistant_content=safe_msg.get("content") or "",
            )
            if success_memory:
                memory_store.append_message(session_id, success_memory)

    async for event in step_summary_streamer(
        model_name=assistant_model_id,
        messages=messages,
        session_id=session_id,
        max_steps=max_steps,
        memory_store=memory_store,
    ):
        yield event


def build_successful_execution_memory(
    *,
    session_id: str,
    context: dict,
    exec_trace: list[dict],
    assistant_content: str,
) -> dict | None:
    if not assistant_task_enabled("memory_compression"):
        return None
    if not exec_trace:
        return None
    if any(item.get("status") not in {"done", None, ""} for item in exec_trace):
        return None
    steps = []
    for index, item in enumerate(exec_trace, start=1):
        tool = item.get("tool") or "unknown"
        args = str(item.get("args") or "").strip()
        result = str(item.get("result") or "").strip()
        steps.append(
            f"{index}. 工具={tool}; 执行={args[:500] or '-'}; 成功结果={result[:700] or '-'}"
        )
    content = f"""
【成功执行经验】
会话：{session_id}
资产：{context.get('asset_type')}/{context.get('protocol')} {context.get('host')}:{context.get('port')}
模式：{'可修改' if context.get('allow_modifications') else '只读'}
结论：本轮工具链全部执行成功，可作为后续同类资产排查的参考路径。
确认方式：辅助模型根据上下文自确认；未配置辅助模型时由主模型接管。无需用户每次点赞，但如果用户点踩对应回答，后续压缩必须否决正向沉淀。

成功步骤：
{chr(10).join(steps)}

AI 输出摘要：
{assistant_content[:1200] or '-'}

沉淀要求：后续长期记忆压缩时保留可复用的排查路径、命令模式、成功信号和注意事项；不要保存密码、Token、密钥或完整敏感连接串。
""".strip()
    return {
        "role": "system",
        "content": content,
        "memory_type": "successful_execution",
    }


def _attach_memory_references_if_visible(
    message: dict,
    pending_references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not pending_references:
        return []
    if str(message.get("content") or "").strip():
        message["memory_refs"] = pending_references
        return []
    return pending_references


def _memory_references_sse_event(message: dict) -> str | None:
    refs = message.get("memory_refs") or message.get("memoryRefs")
    if isinstance(refs, list) and refs:
        return sse_event({"type": "memory_refs", "refs": refs})
    return None
