import asyncio
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


class TestHeadlessApproval(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_headless_approval_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _store_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_headless_approval_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / "approvals.json"

    def test_headless_blocks_and_audits_approval_required_tool_call(self):
        from connections.ssh_manager import ssh_manager
        from core import agent, approval_queue

        store_path = self._store_path("blocked")
        session_id = "sid-headless-risk"
        fake_sessions = {
            session_id: {
                "info": {
                    "session_id": session_id,
                    "host": "10.0.0.21",
                    "port": 22,
                    "username": "root",
                    "password": "managed-secret",
                    "asset_type": "linux",
                    "protocol": "ssh",
                    "allow_modifications": True,
                    "active_skills": [],
                    "agent_profile": "master",
                    "extra_args": {},
                    "target_scope": "asset",
                }
            }
        }
        execute_calls = 0

        async def fake_execute_chat_stream(model_name, messages, thinking_mode, tools=None):
            nonlocal execute_calls
            execute_calls += 1
            if execute_calls == 1:
                yield {
                    "type": "tool_calls",
                    "tool_calls": [
                        {
                            "id": "headless-call-1",
                            "function": {
                                "name": "linux_execute_command",
                                "arguments": json.dumps({"command": "systemctl restart nginx"}),
                            },
                        }
                    ],
                }
            else:
                yield {"type": "content", "content": "已阻断高风险后台操作。"}

        route_mock = AsyncMock(return_value='{"status":"OK"}')
        with (
            patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path),
            patch.dict(ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.llm_factory.get_client_for_model", return_value=(object(), {})),
            patch("core.llm_execution.execute_chat_stream", fake_execute_chat_stream),
            patch.object(agent.dispatcher, "route_and_execute", route_mock),
        ):
            result = asyncio.run(
                agent.headless_agent_chat(
                    session_id,
                    "后台自动处理告警",
                    inherited_allow_mod=True,
                    model_name="fake-model",
                )
            )
            rejected = approval_queue.list_approval_requests(status="rejected")

        route_mock.assert_not_awaited()
        self.assertIn("协同任务报告", result)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["id"], "headless-call-1")
        self.assertEqual(rejected[0]["tool_name"], "linux_execute_command")
        self.assertEqual(rejected[0]["operator"], "system")
        self.assertEqual(rejected[0]["context"]["execution_mode"], "headless")
        self.assertNotIn("managed-secret", json.dumps(rejected[0], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
