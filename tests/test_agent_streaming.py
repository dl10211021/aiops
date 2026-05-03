import unittest

from core.agent_sse import sse_event
from core.agent_streaming import AgentStreamState, stream_assistant_response


async def collect_stream_events(chunks, *, cancel_requested=lambda: False):
    async def executor(model_name, messages, thinking_mode, tools=None):
        for chunk in chunks:
            yield chunk

    state = AgentStreamState()
    events = []
    async for event in stream_assistant_response(
        model_name="model",
        messages=[{"role": "user", "content": "hi"}],
        thinking_mode="on",
        tools=[{"name": "tool"}],
        state=state,
        cancel_requested=cancel_requested,
        stream_executor=executor,
    ):
        events.append(event)
    return events, state


class AgentStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_thinking_and_content_with_balanced_think_tags(self):
        events, state = await collect_stream_events(
            [
                {"type": "thinking", "content": "分析"},
                {"type": "content", "content": "结果"},
            ]
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "chunk", "content": "<think>\n"}),
                sse_event({"type": "chunk", "content": "分析"}),
                sse_event({"type": "chunk", "content": "\n</think>\n"}),
                sse_event({"type": "chunk", "content": "结果"}),
            ],
        )
        self.assertEqual(state.thinking_content, "分析")
        self.assertEqual(state.assistant_content, "结果")
        self.assertEqual(
            state.assistant_message(),
            {
                "role": "assistant",
                "content": "结果",
                "reasoning_content": "分析",
            },
        )

    async def test_records_tool_calls_without_emitting_content_event(self):
        tool_calls = [{"id": "call-1", "function": {"name": "inspect"}}]
        events, state = await collect_stream_events(
            [{"type": "tool_calls", "tool_calls": tool_calls}]
        )

        self.assertEqual(events, [])
        self.assertEqual(state.tool_calls, tool_calls)
        self.assertEqual(
            state.assistant_message(),
            {"role": "assistant", "content": "", "tool_calls": tool_calls},
        )

    async def test_cancel_closes_open_thinking_stream(self):
        cancel_checks = iter([False, True])

        events, state = await collect_stream_events(
            [
                {"type": "thinking", "content": "先想"},
                {"type": "content", "content": "不应出现"},
            ],
            cancel_requested=lambda: next(cancel_checks),
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "chunk", "content": "<think>\n"}),
                sse_event({"type": "chunk", "content": "先想"}),
                sse_event({"type": "chunk", "content": "\n</think>\n"}),
            ],
        )
        self.assertEqual(state.thinking_content, "先想")
        self.assertEqual(state.assistant_content, "")


if __name__ == "__main__":
    unittest.main()
