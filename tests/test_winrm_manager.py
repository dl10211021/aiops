import sys
import types
import unittest
from unittest.mock import patch

from connections.winrm_manager import WinRMExecutor


class FakeWinRMResult:
    def __init__(self, status_code=0, stdout=b"ok", stderr=b""):
        self.status_code = status_code
        self.std_out = stdout
        self.std_err = stderr


class FakeWinRMSession:
    last = None
    next_result = None
    next_exception = None

    def __init__(self, endpoint, auth, transport):
        self.endpoint = endpoint
        self.auth = auth
        self.transport = transport
        self.ps_script = None
        self.cmd_command = None
        FakeWinRMSession.last = self

    def run_ps(self, script):
        if FakeWinRMSession.next_exception:
            raise FakeWinRMSession.next_exception
        self.ps_script = script
        return FakeWinRMSession.next_result or FakeWinRMResult()

    def run_cmd(self, command):
        if FakeWinRMSession.next_exception:
            raise FakeWinRMSession.next_exception
        self.cmd_command = command
        return FakeWinRMSession.next_result or FakeWinRMResult(stdout=b"cmd-ok")


class TestWinRMExecutor(unittest.TestCase):
    def setUp(self):
        FakeWinRMSession.last = None
        FakeWinRMSession.next_result = None
        FakeWinRMSession.next_exception = None

    def _fake_winrm_module(self):
        return types.SimpleNamespace(Session=FakeWinRMSession)

    def test_powershell_script_is_passed_to_run_ps_without_rewriting(self):
        command = (
            "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; "
            "StartTime=(Get-Date).AddDays(-1)} -MaxEvents 20 | "
            "Where-Object {$_.ProviderName -like '*Service*'} | "
            "Select-Object TimeCreated,Id,@{Name='Provider';Expression={$_.ProviderName}}"
        )

        with patch.dict(sys.modules, {"winrm": self._fake_winrm_module()}):
            result = WinRMExecutor().execute_command(
                host="win.local",
                port=5985,
                username="administrator",
                password="secret",
                command=command,
                extra_args={},
            )

        self.assertTrue(result["success"])
        self.assertEqual(FakeWinRMSession.last.ps_script, command)
        self.assertIsNone(FakeWinRMSession.last.cmd_command)

    def test_cmd_shell_still_uses_run_cmd(self):
        with patch.dict(sys.modules, {"winrm": self._fake_winrm_module()}):
            result = WinRMExecutor().execute_command(
                host="win.local",
                port=5985,
                username="administrator",
                password="secret",
                command="whoami",
                extra_args={"shell": "cmd"},
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "cmd-ok")
        self.assertEqual(FakeWinRMSession.last.cmd_command, "whoami")
        self.assertIsNone(FakeWinRMSession.last.ps_script)

    def test_powershell_parser_error_is_classified(self):
        FakeWinRMSession.next_result = FakeWinRMResult(
            status_code=1,
            stdout=b"",
            stderr=b"ParserError: Missing closing '}' in statement block.",
        )

        with patch.dict(sys.modules, {"winrm": self._fake_winrm_module()}):
            result = WinRMExecutor().execute_command(
                host="win.local",
                port=5985,
                username="administrator",
                password="secret",
                command="Get-Service | Where-Object {$_.Status -ne 'Running'",
                extra_args={},
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "powershell_syntax")
        self.assertIn("PowerShell", result["error"])
        self.assertIn("ParserError", result["raw_error"])

    def test_security_log_permission_error_is_classified(self):
        FakeWinRMSession.next_result = FakeWinRMResult(
            status_code=1,
            stdout=b"",
            stderr=b"Get-WinEvent : Access is denied",
        )

        with patch.dict(sys.modules, {"winrm": self._fake_winrm_module()}):
            result = WinRMExecutor().execute_command(
                host="win.local",
                port=5985,
                username="operator",
                password="secret",
                command="Get-WinEvent -LogName Security -MaxEvents 10",
                extra_args={},
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "permission_denied")
        self.assertIn("Event Log Readers", result["hint"])

    def test_winrm_transport_exception_is_classified(self):
        FakeWinRMSession.next_exception = TimeoutError("Connection timed out")

        with patch.dict(sys.modules, {"winrm": self._fake_winrm_module()}):
            result = WinRMExecutor().execute_command(
                host="win.local",
                port=5985,
                username="administrator",
                password="secret",
                command="whoami",
                extra_args={},
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "winrm_connection")
        self.assertEqual(result["raw_error"], "Connection timed out")


if __name__ == "__main__":
    unittest.main()
