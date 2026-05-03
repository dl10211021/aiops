import asyncio
import json
import unittest

from core.dispatcher_scope_tools import _aggregate_scope_outputs, execute_on_scope_tool


class DispatcherScopeToolsTests(unittest.TestCase):
    def test_execute_on_scope_rejects_empty_command_before_session_lookup(self):
        result = asyncio.run(execute_on_scope_tool({"scope_target": "ALL", "command": ""}, {}))

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("不能为空", payload["error"])

    def test_aggregate_scope_outputs_groups_identical_output(self):
        aggregated = _aggregate_scope_outputs(
            [
                ("host-a", {"success": True, "output": "ok"}),
                ("host-b", {"success": True, "output": "ok"}),
                ("host-c", {"success": False, "error": "failed"}),
            ]
        )

        self.assertEqual(aggregated["2 hosts returned this output"]["hosts"], ["host-a", "host-b"])
        self.assertEqual(aggregated["2 hosts returned this output"]["output"], "ok")
        self.assertEqual(aggregated["1 hosts returned this output"]["output"], "failed")


if __name__ == "__main__":
    unittest.main()
