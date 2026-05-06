import asyncio
import unittest

from core import chat_runs


class TestChatRuns(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        for run in list(chat_runs._active_runs.values()):
            run.cancel()
        chat_runs._active_runs.clear()
        chat_runs._stop_requested_sessions.clear()

    async def test_cancel_chat_run_hides_running_state_immediately(self):
        gate = asyncio.Event()

        async def source():
            yield 'data: {"type":"chunk","content":"running"}\n\n'
            await gate.wait()

        chat_runs.start_chat_run("sid-1", source)

        self.assertTrue(chat_runs.is_chat_running("sid-1"))
        self.assertTrue(chat_runs.cancel_chat_run("sid-1"))

        self.assertFalse(chat_runs.is_chat_running("sid-1"))
        await asyncio.sleep(0)

    async def test_start_chat_run_replaces_stopped_run(self):
        gate = asyncio.Event()

        async def first_source():
            yield 'data: {"type":"chunk","content":"first"}\n\n'
            await gate.wait()

        async def second_source():
            yield 'data: {"type":"chunk","content":"second"}\n\n'

        first_run = chat_runs.start_chat_run("sid-1", first_source)
        chat_runs.cancel_chat_run("sid-1")

        second_run = chat_runs.start_chat_run("sid-1", second_source)

        self.assertIsNot(first_run, second_run)
        self.assertNotIn("sid-1", chat_runs._stop_requested_sessions)


if __name__ == "__main__":
    unittest.main()
