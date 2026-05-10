from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

from core.agent_sse import sse_event


StreamExecutor = Callable[
    [str, list[dict], str, Any],
    AsyncIterator[dict],
]


@dataclass
class AgentStreamState:
    assistant_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict] = field(default_factory=list)

    def assistant_message(self) -> dict:
        message = {"role": "assistant", "content": self.assistant_content}
        if self.thinking_content:
            message["reasoning_content"] = self.thinking_content
        if self.tool_calls:
            message["tool_calls"] = self.tool_calls
        return message


async def stream_assistant_response(
    *,
    model_name: str,
    messages: list[dict],
    thinking_mode: str,
    tools: list[dict] | None,
    state: AgentStreamState,
    cancel_requested: Callable[[], bool],
    tool_choice: str = "auto",
    stream_executor: StreamExecutor | None = None,
) -> AsyncIterator[str]:
    if stream_executor is None:
        from core.llm_execution import execute_chat_stream

        stream_executor = execute_chat_stream

    is_thinking_stream = False
    async for chunk in stream_executor(
        model_name,
        messages,
        thinking_mode,
        tools=tools,
        tool_choice=tool_choice,
    ):
        if cancel_requested():
            break
        if chunk["type"] == "thinking":
            if not is_thinking_stream:
                yield sse_event({"type": "chunk", "content": "<think>\n"})
                is_thinking_stream = True
            yield sse_event({"type": "chunk", "content": chunk["content"]})
            state.thinking_content += chunk["content"]
        elif chunk["type"] == "content":
            if is_thinking_stream:
                yield sse_event({"type": "chunk", "content": "\n</think>\n"})
                is_thinking_stream = False
            yield sse_event({"type": "chunk", "content": chunk["content"]})
            state.assistant_content += chunk["content"]
        elif chunk["type"] == "tool_calls":
            if is_thinking_stream:
                yield sse_event({"type": "chunk", "content": "\n</think>\n"})
                is_thinking_stream = False
            state.tool_calls = chunk["tool_calls"]

    if is_thinking_stream:
        yield sse_event({"type": "chunk", "content": "\n</think>\n"})
