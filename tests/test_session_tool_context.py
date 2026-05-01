import json
import unittest

from core.session_tool_context import (
    build_session_tool_context,
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
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)
