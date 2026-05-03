import json
import unittest
from unittest.mock import patch

from core.agent_tool_events import (
    invalid_tool_arguments_result,
    prepare_tool_call,
)


class AgentToolCallPreparationTests(unittest.TestCase):
    def test_prepare_tool_call_parses_arguments_and_redacts_display_command(self):
        prepared = prepare_tool_call(
            {
                "id": "call-1",
                "function": {
                    "name": "linux_execute_command",
                    "arguments": json.dumps(
                        {"command": "echo sk-1234567890abcdef"}
                    ),
                },
            }
        )

        self.assertEqual(prepared.id, "call-1")
        self.assertEqual(prepared.name, "linux_execute_command")
        self.assertEqual(prepared.args, {"command": "echo sk-1234567890abcdef"})
        self.assertIsNone(prepared.parse_error)
        self.assertIn("echo", prepared.display_cmd)
        self.assertNotIn("sk-1234567890abcdef", prepared.display_cmd)

    def test_prepare_tool_call_reports_parse_error_without_arguments(self):
        with patch(
            "core.agent_tool_events.parse_tool_arguments",
            side_effect=ValueError("bad json"),
        ):
            prepared = prepare_tool_call(
                {
                    "id": "call-2",
                    "function": {
                        "name": "db_execute_query",
                        "arguments": "{bad",
                    },
                }
            )

        self.assertEqual(prepared.id, "call-2")
        self.assertEqual(prepared.name, "db_execute_query")
        self.assertEqual(prepared.args, {})
        self.assertEqual(prepared.parse_error, "bad json")
        self.assertEqual(prepared.display_cmd, "JSON解析失败: bad json")

    def test_invalid_tool_arguments_result_preserves_existing_error_contract(self):
        result = json.loads(invalid_tool_arguments_result("bad json"))

        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["error_type"], "tool_arguments_invalid")
        self.assertIn("bad json", result["error"])
        self.assertIn("复杂 PowerShell/SQL", result["hint"])


if __name__ == "__main__":
    unittest.main()
