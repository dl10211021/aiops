import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.agent import chat_stream_agent
from core.session_target_guard import find_session_target_mismatch


class SessionTargetGuardTests(unittest.IsolatedAsyncioTestCase):
    def test_detects_explicit_target_mismatch(self):
        mismatch = find_session_target_mismatch(
            "请对当前资产 linux/ssh 192.168.122.95 执行一次完整只读巡检。",
            {
                "asset_type": "oracle",
                "protocol": "oracle",
                "host": "172.17.1.207",
            },
        )

        self.assertIsNotNone(mismatch)
        self.assertEqual(mismatch.requested_asset_type, "linux")
        self.assertEqual(mismatch.current_asset_type, "oracle")

    def test_allows_current_session_target(self):
        mismatch = find_session_target_mismatch(
            "请对当前资产 oracle/oracle 172.17.1.207 执行一次完整只读巡检。",
            {
                "asset_type": "oracle",
                "protocol": "oracle",
                "host": "172.17.1.207",
            },
        )

        self.assertIsNone(mismatch)

    async def test_chat_stream_agent_blocks_mismatched_target_before_model(self):
        class FakeMemory:
            def __init__(self):
                self.messages = []

            def append_message(self, session_id, message):
                self.messages.append((session_id, message))
                return len(self.messages)

        class FakeDispatcher:
            def get_active_skill_paths(self, active_skills):
                return []

        fake_memory = FakeMemory()
        active_sessions = {
            "sid-oracle": {
                "info": {
                    "asset_type": "oracle",
                    "protocol": "oracle",
                    "host": "172.17.1.207",
                    "port": 1521,
                    "username": "system",
                    "active_skills": ["database"],
                    "extra_args": {},
                }
            }
        }

        with (
            patch("connections.ssh_manager.ssh_manager.active_sessions", active_sessions),
            patch("core.agent.memory_db", fake_memory),
            patch("core.agent.dispatcher", FakeDispatcher()),
            patch("core.agent.prepare_chat_agent_run") as prepare_run,
        ):
            events = [
                event
                async for event in chat_stream_agent(
                    session_id="sid-oracle",
                    user_message="请对当前资产 linux/ssh 192.168.122.95 执行一次完整只读巡检。",
                    user_display_message=None,
                    model_name="test-model",
                )
            ]

        prepare_run.assert_not_called()
        self.assertEqual([item[1]["role"] for item in fake_memory.messages], ["user", "assistant"])
        self.assertIn("已拦截本次请求", fake_memory.messages[-1][1]["content"])
        payloads = [
            json.loads(line.removeprefix("data: "))
            for event in events
            for line in event.splitlines()
            if line.startswith("data: ")
        ]
        self.assertEqual(payloads[-1]["type"], "done")
        self.assertEqual(payloads[0]["type"], "chunk")
        self.assertIn("linux/ssh 192.168.122.95", payloads[0]["content"])

    async def test_analysis_only_chat_skips_target_mismatch_guard(self):
        class FakeDispatcher:
            def get_active_skill_paths(self, active_skills):
                return []

        async def fake_loop(**_kwargs):
            yield 'data: {"type":"done"}\n\n'

        active_sessions = {
            "sid-linux": {
                "info": {
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "host": "172.17.10.2",
                    "port": 22,
                    "username": "root",
                    "active_skills": [],
                    "extra_args": {},
                }
            }
        }
        fake_run = SimpleNamespace(
            model_name="test-model",
            embedding_client=None,
            embedding_model="",
            messages=[],
            context={"analysis_only": True},
            tools=[],
            memory_references=[],
        )

        with (
            patch("connections.ssh_manager.ssh_manager.active_sessions", active_sessions),
            patch("core.agent.dispatcher", FakeDispatcher()),
            patch("core.agent.prepare_chat_agent_run", return_value=fake_run) as prepare_run,
            patch("core.agent.run_chat_agent_loop", fake_loop),
        ):
            events = [
                event
                async for event in chat_stream_agent(
                    session_id="sid-linux",
                    user_message="【SSH终端记录】\n```text\n              total        used        free      shared  buff/cache   available\n```",
                    user_display_message=None,
                    model_name="test-model",
                    analysis_only=True,
                )
            ]

        prepare_run.assert_called_once()
        self.assertTrue(prepare_run.call_args.kwargs["analysis_only"])
        self.assertEqual(events, ['data: {"type":"done"}\n\n'])


if __name__ == "__main__":
    unittest.main()
