import asyncio
import json
import unittest
from unittest.mock import patch

from core.legacy_command_service import (
    LegacyCommandServiceError,
    execute_legacy_command_record,
    map_legacy_execute_tool_call,
)


class FakeTool:
    def __init__(self, name):
        self.name = name


class FakeToolRegistry:
    def __init__(self, names=None):
        self.names = names or []
        self.available_contexts = []

    def available(self, context):
        self.available_contexts.append(context)
        return [FakeTool(name) for name in self.names]


class FakeDispatcher:
    def __init__(self, response=None, requires_approval=False):
        self.response = response or json.dumps({"success": True, "output": "ok"})
        self.requires_approval = requires_approval
        self.checks = []
        self.executions = []

    def check_approval_needed(self, tool_name, tool_args, context):
        self.checks.append((tool_name, tool_args, context))
        return self.requires_approval, "risk"

    async def route_and_execute(self, tool_name, tool_args, context):
        self.executions.append((tool_name, tool_args, context))
        return self.response


def session_info(asset_type: str, protocol: str, extra_args: dict | None = None) -> dict:
    return {
        "host": "target.local",
        "port": 3306,
        "username": "managed_user",
        "password": "managed_secret",
        "asset_type": asset_type,
        "protocol": protocol,
        "extra_args": extra_args or {},
        "allow_modifications": False,
        "target_scope": "asset",
    }


class TestLegacyCommandService(unittest.TestCase):
    def test_execute_sql_session_routes_through_dispatcher(self):
        sessions = {"sid-db": {"info": session_info("mysql", "mysql", {"db_type": "mysql"})}}
        dispatcher = FakeDispatcher(response=json.dumps({"success": True, "data": [{"one": 1}]}))

        result = asyncio.run(
            execute_legacy_command_record(
                sessions,
                FakeToolRegistry(),
                session_id="sid-db",
                command="SELECT 1",
                dispatcher=dispatcher,
            )
        )

        self.assertEqual(result["output"], [{"one": 1}])
        self.assertEqual(dispatcher.executions[0][0], "db_execute_query")
        self.assertEqual(dispatcher.executions[0][1], {"sql": "SELECT 1"})
        self.assertEqual(dispatcher.executions[0][2]["session_id"], "sid-db")

    def test_approval_required_error_prevents_dispatcher_execution(self):
        sessions = {"sid-db": {"info": session_info("mysql", "mysql", {"db_type": "mysql"})}}
        dispatcher = FakeDispatcher(requires_approval=True)

        with self.assertRaises(LegacyCommandServiceError) as ctx:
            asyncio.run(
                execute_legacy_command_record(
                    sessions,
                    FakeToolRegistry(),
                    session_id="sid-db",
                    command="UPDATE users SET disabled = 1",
                    dispatcher=dispatcher,
                )
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(dispatcher.executions, [])

    def test_non_json_dispatcher_result_returns_bad_request(self):
        sessions = {"sid-linux": {"info": session_info("linux", "ssh")}}
        dispatcher = FakeDispatcher(response="plain failure")

        with self.assertRaises(LegacyCommandServiceError) as ctx:
            asyncio.run(
                execute_legacy_command_record(
                    sessions,
                    FakeToolRegistry(),
                    session_id="sid-linux",
                    command="uptime",
                    dispatcher=dispatcher,
                )
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "plain failure")

    def test_missing_session_returns_not_found(self):
        with self.assertRaises(LegacyCommandServiceError) as ctx:
            asyncio.run(
                execute_legacy_command_record(
                    {},
                    FakeToolRegistry(),
                    session_id="missing",
                    command="uptime",
                    dispatcher=FakeDispatcher(),
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)

    def test_execute_uses_default_dispatcher_when_not_injected(self):
        sessions = {"sid-linux": {"info": session_info("linux", "ssh")}}
        dispatcher = FakeDispatcher(response=json.dumps({"success": True, "output": "ok"}))

        with patch("core.legacy_command_service.dispatcher_module.dispatcher", dispatcher):
            result = asyncio.run(
                execute_legacy_command_record(
                    sessions,
                    FakeToolRegistry(),
                    session_id="sid-linux",
                    command="uptime",
                )
            )

        self.assertEqual(result["output"], "ok")
        self.assertEqual(dispatcher.executions[0][0], "linux_execute_command")

    def test_http_api_mapping_prefers_registered_specific_tool(self):
        registry = FakeToolRegistry(["http_api_request", "database_api_request"])

        tool_name, tool_args = map_legacy_execute_tool_call(
            {"asset_type": "clickhouse", "protocol": "http_api", "extra_args": {"category": "db"}},
            "POST /?query=SELECT%201",
            registry,
        )

        self.assertEqual(tool_name, "database_api_request")
        self.assertEqual(tool_args, {"method": "POST", "path": "/?query=SELECT%201"})
        self.assertEqual(registry.available_contexts[0]["protocol"], "http_api")


if __name__ == "__main__":
    unittest.main()
