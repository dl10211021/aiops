import unittest

from core.agent_runtime_config import agent_step_limit_instruction
from core.agent_sse import sse_event
from core.agent_step_summary import stream_step_limit_summary


class FakeMemoryStore:
    def __init__(self):
        self.messages = []

    def append_message(self, session_id, message):
        self.messages.append((session_id, message))


async def collect_step_summary_events(chunks_or_error):
    async def executor(model_name, messages, thinking_mode, tools=None):
        if isinstance(chunks_or_error, Exception):
            raise chunks_or_error
        for chunk in chunks_or_error:
            yield chunk

    messages = [{"role": "assistant", "content": "工具结果"}]
    memory_store = FakeMemoryStore()
    events = []
    async for event in stream_step_limit_summary(
        model_name="model-a",
        messages=messages,
        session_id="sid-1",
        max_steps=2,
        memory_store=memory_store,
        stream_executor=executor,
    ):
        events.append(event)
    return events, messages, memory_store


class AgentStepSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_summary_chunks_and_persists_final_message(self):
        events, messages, memory_store = await collect_step_summary_events(
            [
                {"type": "thinking", "content": "分析"},
                {"type": "content", "content": "阶段"},
                {"type": "content", "content": "报告"},
            ]
        )

        self.assertEqual(
            events,
            [
                sse_event(
                    {
                        "type": "status",
                        "content": "已达到 2 步执行保护上限，正在整理阶段性报告...",
                    },
                    ensure_ascii=False,
                ),
                sse_event({"type": "chunk", "content": "阶段"}, ensure_ascii=False),
                sse_event({"type": "chunk", "content": "报告"}, ensure_ascii=False),
                sse_event({"type": "done"}),
            ],
        )
        self.assertEqual(messages[-1], {"role": "assistant", "content": "阶段报告"})
        self.assertEqual(memory_store.messages, [("sid-1", messages[-1])])

    async def test_emits_fallback_when_model_returns_no_content(self):
        events, messages, memory_store = await collect_step_summary_events(
            [{"type": "thinking", "content": "分析"}]
        )

        fallback = (
            "已达到 2 步执行保护上限，系统已停止继续调用工具。"
            "当前模型未能生成阶段性报告，请根据上方工具结果继续拆分任务。"
        )
        self.assertEqual(
            events[-2:],
            [
                sse_event({"type": "chunk", "content": fallback}, ensure_ascii=False),
                sse_event({"type": "done"}),
            ],
        )
        self.assertEqual(messages[-1], {"role": "assistant", "content": fallback})
        self.assertEqual(memory_store.messages, [("sid-1", messages[-1])])

    async def test_emits_failure_summary_when_executor_raises(self):
        events, messages, memory_store = await collect_step_summary_events(
            RuntimeError("llm down")
        )

        fallback = (
            "已达到 2 步执行保护上限，且阶段性报告生成失败：llm down。"
            "请将任务拆成更小范围后重试。"
        )
        self.assertEqual(
            events[-2:],
            [
                sse_event({"type": "chunk", "content": fallback}, ensure_ascii=False),
                sse_event({"type": "done"}),
            ],
        )
        self.assertEqual(messages[-1], {"role": "assistant", "content": fallback})
        self.assertEqual(memory_store.messages, [("sid-1", messages[-1])])

    async def test_summary_instruction_is_added_without_mutating_source_history_first(self):
        seen_messages = []

        async def executor(model_name, messages, thinking_mode, tools=None):
            seen_messages.extend(messages)
            yield {"type": "content", "content": "ok"}

        source_messages = [{"role": "assistant", "content": "原始"}]
        memory_store = FakeMemoryStore()
        async for _ in stream_step_limit_summary(
            model_name="model-a",
            messages=source_messages,
            session_id="sid-1",
            max_steps=2,
            memory_store=memory_store,
            stream_executor=executor,
        ):
            pass

        self.assertEqual(source_messages[0], {"role": "assistant", "content": "原始"})
        self.assertEqual(seen_messages[-1]["content"], agent_step_limit_instruction(2))


if __name__ == "__main__":
    unittest.main()
