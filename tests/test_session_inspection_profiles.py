import asyncio
import unittest

from core.session_inspection_profiles import http_probe_url, inspect_linux_ssh


class FakeSSHClient:
    def __init__(self):
        self.commands = []

    def execute_command(self, session_id, command, timeout=30):
        self.commands.append((session_id, command, timeout))
        return {"success": True, "output": command, "exit_status": 0}


class SessionInspectionProfilesTest(unittest.TestCase):
    def test_linux_profile_uses_readonly_command_catalog(self):
        ssh = FakeSSHClient()
        report = asyncio.run(inspect_linux_ssh("sid", "linux", "ssh", ssh))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "linux")
        self.assertTrue(any("uname" in command for _, command, _ in ssh.commands))
        self.assertTrue(any("df -hP" in command for _, command, _ in ssh.commands))

    def test_http_probe_url_normalizes_relative_health_path(self):
        url = http_probe_url(
            {
                "host": "api.local",
                "port": 8080,
                "extra_args": {"scheme": "http", "health_path": "healthz"},
            },
            "custom_api",
        )

        self.assertEqual(url, "http://api.local:8080/healthz")


if __name__ == "__main__":
    unittest.main()
