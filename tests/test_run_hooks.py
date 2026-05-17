import unittest

from core.run_hooks import clear_run_hooks, emit_run_hook, register_run_hook


class RunHooksTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        clear_run_hooks()

    async def test_emits_exact_and_wildcard_hooks_with_redacted_payload(self):
        received = []

        def exact(event_type, event):
            received.append(("exact", event_type, event))

        async def wildcard(event_type, event):
            received.append(("wildcard", event_type, event))

        register_run_hook("tool:before", exact)
        register_run_hook("tool:*", wildcard)

        await emit_run_hook(
            "tool:before",
            {
                "session_id": "sid-1",
                "headers": {"Authorization": "Basic secret-token"},
                "password": "secret",
            },
        )

        self.assertEqual([item[0] for item in received], ["exact", "wildcard"])
        self.assertEqual(received[0][1], "tool:before")
        payload = received[0][2]["payload"]
        self.assertEqual(payload["password"], "***")
        self.assertEqual(payload["headers"]["Authorization"], "***")
        self.assertIn("emitted_at", received[0][2])

    async def test_hook_errors_do_not_block_other_handlers(self):
        received = []

        def broken(_event_type, _event):
            raise RuntimeError("boom")

        def working(event_type, event):
            received.append((event_type, event["payload"]["session_id"]))

        register_run_hook("run:start", broken)
        register_run_hook("run:start", working)

        await emit_run_hook("run:start", {"session_id": "sid-1"})

        self.assertEqual(received, [("run:start", "sid-1")])

    async def test_unregister_removes_handler(self):
        received = []

        unregister = register_run_hook(
            "run:end",
            lambda event_type, event: received.append((event_type, event)),
        )
        unregister()

        await emit_run_hook("run:end", {"session_id": "sid-1"})

        self.assertEqual(received, [])
