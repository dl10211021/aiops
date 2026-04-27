import asyncio
import json
import unittest
import warnings
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from api import routes


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


class TestExecuteRouteProtocols(unittest.TestCase):
    def test_execute_routes_sql_command_to_db_tool(self):
        fake_sessions = {"sid-db": {"info": session_info("mysql", "mysql", {"db_type": "mysql"})}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "data": [{"one": 1}]})
            response = asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-db", command="SELECT 1")
                )
            )

        self.assertEqual(response.status, "success")
        execute.assert_awaited_once()
        self.assertEqual(execute.await_args.args[0], "db_execute_query")
        self.assertEqual(execute.await_args.args[1], {"sql": "SELECT 1"})

    def test_execute_routes_http_command_to_http_api_tool(self):
        fake_sessions = {"sid-api": {"info": session_info("prometheus", "http_api")}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "output": "{}"})
            asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-api", command="GET /api/v1/status/buildinfo")
                )
            )

        self.assertEqual(execute.await_args.args[0], "http_api_request")
        self.assertEqual(
            execute.await_args.args[1],
            {"method": "GET", "path": "/api/v1/status/buildinfo"},
        )

    def test_execute_routes_snmp_command_to_snmp_get(self):
        fake_sessions = {"sid-snmp": {"info": session_info("snmp", "snmp")}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "data": []})
            asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-snmp", command="1.3.6.1.2.1.1.1.0")
                )
            )

        self.assertEqual(execute.await_args.args[0], "snmp_get")
        self.assertEqual(execute.await_args.args[1], {"oid": "1.3.6.1.2.1.1.1.0"})

    def test_execute_routes_container_ssh_to_container_tool(self):
        fake_sessions = {"sid-docker": {"info": session_info("docker", "ssh")}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "output": "ok"})
            asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-docker", command="docker ps")
                )
            )

        self.assertEqual(execute.await_args.args[0], "container_execute_command")
        self.assertEqual(execute.await_args.args[1], {"command": "docker ps"})

    def test_execute_routes_firewall_ssh_to_network_cli_tool(self):
        fake_sessions = {"sid-fw": {"info": session_info("firewall", "ssh")}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "output": "ok"})
            asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-fw", command="display version")
                )
            )

        self.assertEqual(execute.await_args.args[0], "network_cli_execute_command")

    def test_execute_routes_mongodb_json_to_find_tool(self):
        fake_sessions = {"sid-mongo": {"info": session_info("mongodb", "mongodb", {"database": "admin"})}}
        command = json.dumps({"collection": "system.version", "filter": {"_id": "featureCompatibilityVersion"}, "limit": 5})

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            execute.return_value = json.dumps({"success": True, "data": []})
            asyncio.run(
                routes.execute_remote_command(
                    routes.CommandRequest(session_id="sid-mongo", command=command)
                )
            )

        self.assertEqual(execute.await_args.args[0], "mongodb_find")
        self.assertEqual(execute.await_args.args[1]["collection"], "system.version")
        self.assertEqual(execute.await_args.args[1]["filter"], {"_id": "featureCompatibilityVersion"})
        self.assertEqual(execute.await_args.args[1]["limit"], 5)

    def test_execute_rejects_high_risk_command_that_requires_chat_approval(self):
        info = session_info("mysql", "mysql", {"db_type": "mysql"})
        info["allow_modifications"] = True
        fake_sessions = {"sid-db": {"info": info}}

        with (
            patch.dict(routes.ssh_manager.active_sessions, fake_sessions, clear=True),
            patch("core.dispatcher.dispatcher.route_and_execute", new_callable=AsyncMock) as execute,
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    routes.execute_remote_command(
                        routes.CommandRequest(session_id="sid-db", command="UPDATE users SET disabled = 1")
                    )
                )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("需要后端审批", str(ctx.exception.detail))
        execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
