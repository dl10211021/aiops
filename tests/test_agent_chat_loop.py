import unittest

from core.agent_chat_loop import run_chat_agent_loop
from core.agent_sse import sse_event


class FakeMemoryStore:
    def __init__(self):
        self.appended = []

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))

    async def compress_and_store_ltm(
        self,
        session_id,
        emb_client,
        embedding_model,
        primary_model_id=None,
        memory_scope_ids=None,
    ):
        return None


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


async def no_sleep(_seconds):
    return None


async def collect_chat_loop_events(**overrides):
    memory_store = overrides.pop("memory_store", FakeMemoryStore())
    cancel_flags = overrides.pop("cancel_flags", {"sid-1": False})
    scheduler_calls = []

    def scheduler(**kwargs):
        scheduler_calls.append(kwargs)

    base_kwargs = {
        "session_id": "sid-1",
        "model_name": "model-a",
        "thinking_mode": "off",
        "messages": [],
        "context": {"session_id": "sid-1", "memory_scope_ids": ["sid-1", "asset:ssh:10.0.0.1:22"]},
        "tools": [{"name": "tool"}],
        "memory_store": memory_store,
        "dispatcher": object(),
        "cancel_flags": cancel_flags,
        "emb_client": "emb-client",
        "embedding_model": "emb-model",
        "event_logger": FakeLogger(),
        "sleep": no_sleep,
        "compression_scheduler": scheduler,
    }
    base_kwargs.update(overrides)
    events = []
    async for event in run_chat_agent_loop(**base_kwargs):
        events.append(event)
    return events, base_kwargs, memory_store, cancel_flags, scheduler_calls


class AgentChatLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_assistant_message_done_and_schedules_ltm(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "完成"
            yield "stream-event"

        events, kwargs, memory_store, _cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(assistant_streamer=streamer)
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."}),
                sse_event({"type": "status", "content": "💭 思考中..."}),
                "stream-event",
                sse_event({"type": "done"}),
            ],
        )
        self.assertEqual(kwargs["messages"], [{"role": "assistant", "content": "完成"}])
        self.assertEqual(memory_store.appended, [("sid-1", kwargs["messages"][0])])
        self.assertEqual(scheduler_calls[0]["session_id"], "sid-1")
        self.assertEqual(scheduler_calls[0]["emb_client"], "emb-client")
        self.assertEqual(
            scheduler_calls[0]["memory_scope_ids"],
            ["sid-1", "asset:ssh:10.0.0.1:22"],
        )

    async def test_cancel_before_streaming_resets_flag_and_schedules_ltm(self):
        async def streamer(**_kwargs):
            raise AssertionError("streamer should not run after cancellation")

        events, _kwargs, _memory_store, cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(
                cancel_flags={"sid-1": True},
                assistant_streamer=streamer,
            )
        )

        self.assertEqual(
            events,
            [
                sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."}),
                sse_event({"type": "error", "content": "任务已被手动中止。"}),
                sse_event({"type": "done"}),
            ],
        )
        self.assertFalse(cancel_flags["sid-1"])
        self.assertEqual(len(scheduler_calls), 1)

    async def test_attaches_memory_references_to_visible_assistant_message(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "基于历史记忆完成"
            yield "stream-event"

        events, kwargs, memory_store, _cancel_flags, _scheduler_calls = (
            await collect_chat_loop_events(
                assistant_streamer=streamer,
                memory_references=[{"scope_id": "sid-1", "summary_preview": "历史偏好"}],
            )
        )

        self.assertIn("stream-event", events)
        self.assertEqual(kwargs["messages"][0]["memory_refs"][0]["summary_preview"], "历史偏好")
        self.assertEqual(memory_store.appended[0][1]["memory_refs"][0]["scope_id"], "sid-1")

    async def test_processes_tools_then_emits_step_limit_summary(self):
        async def streamer(**kwargs):
            kwargs["state"].assistant_content = "需要工具"
            kwargs["state"].tool_calls = [{"id": "call-1"}]
            if False:
                yield "unused"

        tool_processor_calls = []

        async def tool_processor(**kwargs):
            tool_processor_calls.append(kwargs)
            yield "tool-event"

        async def step_summary(**kwargs):
            yield f"summary:{kwargs['max_steps']}"

        events, kwargs, memory_store, _cancel_flags, scheduler_calls = (
            await collect_chat_loop_events(
                assistant_streamer=streamer,
                tool_call_processor=tool_processor,
                step_summary_streamer=step_summary,
                max_steps_resolver=lambda _mode: 1,
            )
        )

        self.assertEqual(events[-2:], ["tool-event", "summary:1"])
        self.assertEqual(tool_processor_calls[0]["iteration"], 0)
        self.assertEqual(tool_processor_calls[0]["messages"], kwargs["messages"])
        self.assertEqual(memory_store.appended[0][1]["tool_calls"], [{"id": "call-1"}])
        self.assertEqual(len(scheduler_calls), 1)


if __name__ == "__main__":
    unittest.main()
