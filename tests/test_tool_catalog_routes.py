import asyncio
import json
import unittest
import warnings
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"'asyncio\.iscoroutinefunction' is deprecated.*",
    category=DeprecationWarning,
    module=r"fastapi\.routing",
)

from fastapi import HTTPException

from api import session_runtime_routes


class TestToolCatalogRoutes(unittest.TestCase):
    def test_platform_tool_catalog_returns_metadata_only(self):
        response = asyncio.run(session_runtime_routes.get_tool_catalog())

        self.assertEqual(response.status, "success")
        payload = response.data
        self.assertIn("toolsets", payload)
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertIn("linux_execute_command", dumped)
        self.assertNotIn("write_file", dumped)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_tool_center_keeps_built_in_tools_without_hermes_branding(self):
        response = asyncio.run(session_runtime_routes.get_tool_center())

        self.assertEqual(response.status, "success")
        payload = response.data
        self.assertGreaterEqual(payload["summary"]["available"], 1)
        self.assertGreaterEqual(payload["summary"]["controlled"], 1)
        tools = {
            tool["name"]: tool
            for toolset in payload["toolsets"]
            for tool in toolset["tools"]
        }
        toolset_ids = {toolset["id"] for toolset in payload["toolsets"]}
        self.assertIn("linux_execute_command", tools)
        self.assertEqual(tools["linux_execute_command"]["status"], "available")
        self.assertTrue(tools["linux_execute_command"]["model_exposed"])
        self.assertIn("write_file", tools)
        self.assertEqual(tools["write_file"]["status"], "controlled")
        self.assertFalse(tools["write_file"]["model_exposed"])
        self.assertFalse(tools["write_file"]["execution_enabled"])
        self.assertIn("session_search", tools)
        self.assertEqual(tools["session_search"]["status"], "not_wired")
        self.assertTrue(all(not item.lower().startswith("hermes") for item in toolset_ids))
        dumped = json.dumps(payload, ensure_ascii=False).lower()
        self.assertNotIn("hermes", dumped)

    def test_session_tool_catalog_is_protocol_aware_and_credential_free(self):
        fake_sessions = {
            "sid-win": {
                "info": {
                    "host": "192.168.42.51",
                    "port": 5985,
                    "username": "administrator",
                    "password": "managed-secret",
                    "asset_type": "windows",
                    "protocol": "winrm",
                    "extra_args": {"api_key": "secret-key", "sub_type": "windows"},
                    "target_scope": "asset",
                }
            }
        }

        with patch.dict(session_runtime_routes.ssh_manager.active_sessions, fake_sessions, clear=True):
            response = asyncio.run(session_runtime_routes.get_session_tools("sid-win"))

        self.assertEqual(response.status, "success")
        payload = response.data
        self.assertEqual(payload["context"]["protocol"], "winrm")
        self.assertIn("winrm_execute_command", payload["active_tools"])
        self.assertNotIn("linux_execute_command", payload["active_tools"])
        tool_details = {item["name"]: item for item in payload["active_tool_details"]}
        self.assertEqual(tool_details["winrm_execute_command"]["label"], "Windows PowerShell 命令")
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("managed-secret", dumped)
        self.assertNotIn("secret-key", dumped)

    def test_session_tool_catalog_missing_session_raises_404(self):
        with patch.dict(session_runtime_routes.ssh_manager.active_sessions, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(session_runtime_routes.get_session_tools("missing"))

        self.assertEqual(ctx.exception.status_code, 404)

    def test_k8s_session_exposes_kubernetes_toolset_and_commands(self):
        fake_sessions = {
            "sid-k8s": {
                "info": {
                    "host": "k8s.local",
                    "port": 6443,
                    "username": "admin",
                    "password": "managed-secret",
                    "asset_type": "k8s",
                    "protocol": "k8s",
                    "extra_args": {"bearer_token": "secret-key", "sub_type": "k8s"},
                    "target_scope": "asset",
                }
            }
        }

        with patch.dict(session_runtime_routes.ssh_manager.active_sessions, fake_sessions, clear=True):
            tools = asyncio.run(session_runtime_routes.get_session_tools("sid-k8s"))
            commands = asyncio.run(session_runtime_routes.get_session_commands("sid-k8s"))

        self.assertIn("k8s_api_request", tools.data["active_tools"])
        self.assertNotIn("http_api_request", tools.data["active_tools"])
        tool_details = {item["name"]: item for item in tools.data["active_tool_details"]}
        self.assertEqual(tool_details["k8s_api_request"]["label"], "Kubernetes 集群 API")
        self.assertEqual(commands.status, "success")
        self.assertTrue(any(cmd["id"] == "inspect" for cmd in commands.data["commands"]))
        dumped = json.dumps({**tools.data, **commands.data}, ensure_ascii=False)
        self.assertNotIn("secret-key", dumped)


if __name__ == "__main__":
    unittest.main()
