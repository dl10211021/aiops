import unittest

from core.run_trace_store import (
    RUN_TRACE_MEMORY_TYPE,
    build_run_trace_message,
    register_session_run_trace_hooks,
)
from core.run_hooks import clear_run_hooks, emit_run_hook


class FakeMemoryStore:
    def __init__(self):
        self.appended = []

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))


class RunTraceStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clear_run_hooks()

    def tearDown(self):
        clear_run_hooks()

    def test_build_run_trace_message_redacts_sensitive_payload(self):
        message = build_run_trace_message(
            "tool:before",
            {
                "session_id": "sid-1",
                "tool_name": "http_api_request",
                "args": {"headers": {"Authorization": "Basic secret"}},
            },
        )

        self.assertIsNotNone(message)
        self.assertEqual(message["memory_type"], RUN_TRACE_MEMORY_TYPE)
        self.assertFalse(message["visible_to_user"])
        self.assertEqual(message["run_event_type"], "tool:before")
        self.assertEqual(message["run_event_payload"]["args"]["headers"]["Authorization"], "***")
        self.assertIn("工具=http_api_request", message["content"])

    async def test_registered_hook_persists_event_to_session_memory(self):
        memory_store = FakeMemoryStore()
        register_session_run_trace_hooks(memory_store)

        await emit_run_hook(
            "run:start",
            {"session_id": "sid-1", "model_name": "model-a"},
        )

        self.assertEqual(len(memory_store.appended), 1)
        self.assertEqual(memory_store.appended[0][0], "sid-1")
        self.assertEqual(memory_store.appended[0][1]["run_event_type"], "run:start")


if __name__ == "__main__":
    unittest.main()
