import asyncio
import json
import unittest
from unittest.mock import patch

from core.dispatcher_api_tools import API_TOOL_NAMES, execute_api_tool


class DispatcherApiToolsTests(unittest.TestCase):
    def test_api_tool_names_cover_service_probe_and_http_families(self):
        self.assertLessEqual(
            {"service_probe_request", "http_api_request", "virtualization_api_request", "storage_api_request"},
            API_TOOL_NAMES,
        )

    def test_virtualization_api_rejects_winrm_hyperv_context(self):
        result = asyncio.run(
            execute_api_tool(
                "virtualization_api_request",
                {"path": "/api"},
                {"asset_type": "hyperv", "protocol": "winrm"},
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("WinRM", payload["error"])

    def test_storage_api_snmp_context_uses_route_callback(self):
        calls = []

        async def route_callback(tool_name, args, context):
            calls.append((tool_name, args, context))
            return json.dumps({"success": True, "tool": tool_name})

        context = {"asset_type": "nas", "protocol": "snmp"}
        result = asyncio.run(
            execute_api_tool(
                "storage_api_request",
                {},
                context,
                route_callback,
            )
        )

        self.assertEqual(json.loads(result)["tool"], "snmp_get")
        self.assertEqual(calls, [("snmp_get", {"oid": "1.3.6.1.2.1.1.1.0"}, context)])

    def test_http_api_request_uses_managed_context_credentials(self):
        with patch("connections.http_api_manager.http_api_executor.request") as request:
            request.return_value = {"success": True, "data": {"health": "ok"}}
            result = asyncio.run(
                execute_api_tool(
                    "http_api_request",
                    {"path": "/health", "method": "GET"},
                    {
                        "asset_type": "api",
                        "host": "api.local",
                        "port": 8080,
                        "username": "ops",
                        "password": "secret",
                        "extra_args": {"token": "managed"},
                    },
                )
            )

        self.assertTrue(json.loads(result)["success"])
        request.assert_called_once_with(
            asset_type="api",
            host="api.local",
            port=8080,
            username="ops",
            password="secret",
            extra_args={"token": "managed"},
            method="GET",
            path="/health",
            headers={},
            body=None,
        )


if __name__ == "__main__":
    unittest.main()
