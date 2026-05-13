from __future__ import annotations

import asyncio
import json
import time
import unittest
from pathlib import Path
from unittest import mock

import core.dispatcher_hermes_tools as dispatcher_hermes_tools
from core.dispatcher import dispatcher
from core.hermes_tool_adapter import (
    HERMES_AGENT_EXCLUDED_TOOL_NAMES,
    HERMES_AGENT_TOOL_NAMES,
    execute_hermes_tool,
)
from core.tool_registry import tool_registry


class HermesToolAdapterTests(unittest.TestCase):
    def test_agent_hermes_tools_are_registered(self) -> None:
        registered = {tool.name for tool in tool_registry.all_tools()}

        self.assertLessEqual(HERMES_AGENT_TOOL_NAMES, registered)

    def test_dangerous_hermes_tools_are_not_registered_for_agent_dispatch(self) -> None:
        registered = {tool.name for tool in tool_registry.all_tools()}

        # web_search is intentionally provided by OpsCore utility tools.
        excluded_should_not_register = HERMES_AGENT_EXCLUDED_TOOL_NAMES - {"web_search"}
        self.assertTrue(excluded_should_not_register.isdisjoint(registered))
        self.assertTrue(
            HERMES_AGENT_EXCLUDED_TOOL_NAMES.isdisjoint(
                dispatcher_hermes_tools.HERMES_DISPATCH_TOOL_NAMES
            )
        )

    def test_hermes_file_tools_are_repo_scoped_and_windows_aware(self) -> None:
        result = json.loads(
            execute_hermes_tool(
                "read_file",
                {"path": "core/tool_registry.py", "offset": 1, "limit": 2},
                {"session_id": "test"},
            )
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("1|", result["content"])

    def test_dispatcher_routes_hermes_todo_tool(self) -> None:
        async def run() -> dict:
            raw = await dispatcher.route_and_execute(
                "todo",
                {"todos": [{"id": "a", "content": "check adapter", "status": "pending"}]},
                {"session_id": "test-hermes-todo"},
            )
            return json.loads(raw)

        result = asyncio.run(run())

        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["todos"][0]["content"], "check adapter")

    def test_image_gen_alias_dispatches_to_image_generate(self) -> None:
        calls: list[str] = []

        class _FakeRegistry:
            def dispatch(self, name: str, args: dict, **kwargs) -> str:
                calls.append(name)
                return json.dumps({"status": "SUCCESS", "tool": name}, ensure_ascii=False)

        with (
            mock.patch("core.hermes_tool_adapter._registry", return_value=_FakeRegistry()),
            mock.patch("core.hermes_tool_adapter.hermes_tool_available", return_value=(True, "")),
        ):
            payload = json.loads(
                execute_hermes_tool(
                    "image_gen",
                    {"prompt": "blue skyline", "aspect_ratio": "landscape"},
                    {"session_id": "test-image-gen"},
                )
            )

        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["tool"], "image_generate")
        self.assertEqual(calls, ["image_generate"])

    def test_dispatcher_rejects_hermes_write_tool_without_routing(self) -> None:
        blocked_path = Path("tests/.tmp/hermes_blocked_write.txt")
        if blocked_path.exists():
            blocked_path.unlink()

        async def run() -> dict:
            raw = await dispatcher.route_and_execute(
                "write_file",
                {"path": str(blocked_path), "content": "should not be written"},
                {"session_id": "test-hermes-write"},
            )
            return json.loads(raw)

        try:
            result = asyncio.run(run())
        finally:
            if blocked_path.exists():
                blocked_path.unlink()

        self.assertEqual(result["error"], "Unknown tool")
        self.assertFalse(blocked_path.exists())

    def test_hermes_browser_tool_timeout_returns_structured_error(self) -> None:
        def slow_tool(name, args, context):
            time.sleep(0.2)
            return json.dumps({"status": "SUCCESS", "tool": name}, ensure_ascii=False)

        with (
            mock.patch.object(dispatcher_hermes_tools, "execute_hermes_tool", slow_tool),
            mock.patch.object(
                dispatcher_hermes_tools,
                "hermes_tool_timeout_seconds",
                lambda _name: 0.01,
            ),
        ):
            raw = asyncio.run(
                dispatcher_hermes_tools.execute_hermes_dispatch_tool(
                    "browser_navigate",
                    {"url": "https://example.invalid"},
                    {"session_id": "timeout-test"},
                )
            )

        result = json.loads(raw)

        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["tool"], "browser_navigate")
        self.assertEqual(result["error_type"], "timeout")
        self.assertIn("换一个可信来源继续", result["hint"])
