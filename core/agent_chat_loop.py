from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

from core.agent_ltm import schedule_ltm_compression
from core.agent_runtime_config import agent_max_steps
from core.agent_sse import sse_event
from core.agent_step_summary import stream_step_limit_summary
from core.agent_streaming import AgentStreamState, stream_assistant_response
from core.agent_tool_loop import process_chat_tool_calls


class ChatLoopMemoryStore(Protocol):
    def append_message(self, session_id: str, message: dict) -> None:
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
    messages: list[dict],
    context: dict,
    tools: list[dict],
    memory_store: ChatLoopMemoryStore,
    dispatcher: Any,
    cancel_flags: dict[str, bool],
    emb_client: Any,
    embedding_model: str,
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

    max_steps = max_steps_resolver("chat")
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
        messages.append(safe_msg)
        memory_store.append_message(session_id, safe_msg)

        if not tool_calls:
            yield sse_event({"type": "done"})
            break

        async for event in tool_call_processor(
            tool_calls=tool_calls,
            session_id=session_id,
            messages=messages,
            memory_store=memory_store,
            dispatcher=dispatcher,
            context=context,
            iteration=iteration,
        ):
            yield event

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
    )
