import asyncio
import unittest

from core.session_inspection_template_runner import run_inspection_template


class FakeSSHClient:
    def __init__(self):
        self.commands = []

    def execute_command(self, session_id, command, timeout=30):
        self.commands.append((session_id, command, timeout))
        return {"success": True, "output": f"ran:{command}", "exit_status": 0}


class SessionInspectionTemplateRunnerTest(unittest.TestCase):
    def test_runs_ssh_template_step_and_builds_report(self):
        ssh = FakeSSHClient()
        template = {
            "id": "custom-linux",
            "name": "Linux",
            "steps": [
                {
                    "name": "hostname",
                    "title": "主机名",
                    "tool": "linux_execute_command",
                    "command": "hostname",
                    "timeout": 7,
                }
            ],
        }

        report = asyncio.run(
            run_inspection_template(
                "sid",
                {"extra_args": {}},
                "linux",
                "ssh",
                template,
                ssh,
            )
        )

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["template_id"], "custom-linux")
        self.assertEqual(report["checks"][0]["output"], "ran:hostname")
        self.assertEqual(ssh.commands, [("sid", "hostname", 7)])

    def test_unsupported_template_tool_returns_warning(self):
        report = asyncio.run(
            run_inspection_template(
                "sid",
                {"extra_args": {}},
                "linux",
                "ssh",
                {
                    "id": "bad-template",
                    "steps": [{"name": "bad", "tool": "unknown_tool", "command": "noop"}],
                },
                FakeSSHClient(),
            )
        )

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["checks"][0]["status"], "error")
        self.assertIn("不支持的巡检工具", report["checks"][0]["output"])


if __name__ == "__main__":
    unittest.main()
