import json
import unittest

from core.session_tool_context import (
    SessionToolContextError,
    build_session_info_for_tools,
    build_session_tool_context,
    build_session_tools_payload_for_session,
    build_session_tools_response,
)
from core.tool_registry import tool_registry


class TestSessionToolContext(unittest.TestCase):
    def test_build_session_tool_context_resolves_identity(self):
        context = build_session_tool_context(
            {
                "session_id": "sid-win",
                "host": "192.168.42.51",
                "port": 5985,
                "asset_type": "windows",
                "protocol": "winrm",
                "extra_args": {"sub_type": "windows", "api_key": "secret-key"},
                "target_scope": "asset",
            }
        )

        self.assertEqual(context["session_id"], "sid-win")
        self.assertEqual(context["asset_type"], "windows")
        self.assertEqual(context["protocol"], "winrm")
        self.assertEqual(context["extra_args"]["api_key"], "secret-key")

    def test_build_session_tools_response_omits_credentials_from_public_context(self):
        payload = build_session_tools_response(
            tool_registry,
            {
                "session_id": "sid-win",
                "host": "192.168.42.51",
                "port": 5985,
                "password": "managed-secret",
                "asset_type": "windows",
                "protocol": "winrm",
                "extra_args": {"sub_type": "windows", "api_key": "secret-key"},
                "target_scope": "asset",
            },
        )

        self.assertEqual(payload["context"]["protocol"], "winrm")
        self.assertIn("winrm_execute_command", payload["active_tools"])
        self.assertNotIn("linux_execute_command", payload["active_tools"])
        tool_details = {item["name"]: item for item in payload["active_tool_details"]}
        self.assertEqual(tool_details["winrm_execute_command"]["label"], "Windows PowerShell 命令")
        self.assertEqual(tool_details["winrm_execute_command"]["operation_mode"], "read_write")
        self.assertEqual(tool_details["winrm_execute_command"]["approval_policy"], "guarded_write")
        self.assertIn("timeout_policy", tool_details["winrm_execute_command"])
        self.assertIn("retry_policy", tool_details["winrm_execute_command"])
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_build_session_info_for_tools_copies_session_info(self):
        sessions = {"sid-1": {"info": {"host": "10.0.0.1", "protocol": "ssh"}}}

        info = build_session_info_for_tools(sessions, "sid-1")

        self.assertEqual(info["session_id"], "sid-1")
        self.assertEqual(info["host"], "10.0.0.1")
        self.assertIsNot(info, sessions["sid-1"]["info"])

    def test_build_session_info_for_tools_rejects_missing_session(self):
        with self.assertRaises(SessionToolContextError) as ctx:
            build_session_info_for_tools({}, "missing")

        self.assertEqual(ctx.exception.status_code, 404)

    def test_build_session_tools_payload_for_session_uses_active_session(self):
        sessions = {
            "sid-win": {
                "info": {
                    "host": "192.168.42.51",
                    "port": 5985,
                    "asset_type": "windows",
                    "protocol": "winrm",
                    "extra_args": {"sub_type": "windows"},
                    "target_scope": "asset",
                }
            }
        }

        payload = build_session_tools_payload_for_session(sessions, tool_registry, "sid-win")

        self.assertEqual(payload["context"]["protocol"], "winrm")
        self.assertIn("winrm_execute_command", payload["active_tools"])
        tool_details = {item["name"]: item for item in payload["active_tool_details"]}
        self.assertEqual(tool_details["winrm_execute_command"]["label"], "Windows PowerShell 命令")
        self.assertEqual(tool_details["winrm_execute_command"]["operation_mode"], "read_write")
