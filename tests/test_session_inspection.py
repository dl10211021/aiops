import asyncio
import unittest
from unittest.mock import patch


class FakeSSHManager:
    def __init__(self, info):
        self.active_sessions = {"sid": {"info": info}}
        self.commands = []

    def execute_command(self, session_id, command, timeout=30):
        self.commands.append(command)
        return {
            "success": True,
            "exit_status": 0,
            "output": f"ok: {command.split()[0]}",
            "has_error": False,
        }

    def execute_network_cli_command(self, session_id, command, timeout=30):
        self.commands.append(command)
        return {
            "success": True,
            "exit_status": 0,
            "output": f"ok: {command.split()[0]}",
            "has_error": False,
        }


class TestSessionInspection(unittest.TestCase):
    def test_linux_ssh_session_runs_read_only_inspection(self):
        from core import session_inspector

        fake = FakeSSHManager({"asset_type": "linux", "protocol": "ssh"})
        with patch.object(session_inspector, "ssh_manager", fake):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertTrue(report["supported"])
        self.assertGreaterEqual(len(report["checks"]), 3)
        self.assertTrue(all(check["status"] == "success" for check in report["checks"]))
        self.assertTrue(any("uname" in command for command in fake.commands))
        self.assertTrue(any("df -hP" in command for command in fake.commands))

    def test_kvm_ssh_session_uses_linux_inspection_profile(self):
        from core import session_inspector

        fake = FakeSSHManager({"asset_type": "kvm", "protocol": "ssh"})
        with patch.object(session_inspector, "ssh_manager", fake):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertTrue(report["supported"])
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-kvm-core-readonly")

    def test_winrm_session_runs_read_only_inspection(self):
        from core import session_inspector

        fake = FakeSSHManager(
            {
                "asset_type": "windows",
                "protocol": "winrm",
                "host": "win.local",
                "port": 5985,
                "username": "admin",
                "password": "secret",
                "extra_args": {},
            }
        )
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch("connections.winrm_manager.winrm_executor.execute_command") as execute_command,
        ):
            execute_command.return_value = {"success": True, "output": "ok"}
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertTrue(report["supported"])
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-windows-core-readonly")
        self.assertGreaterEqual(execute_command.call_count, 5)

    def test_switch_session_runs_network_cli_inspection(self):
        from core import session_inspector

        fake = FakeSSHManager(
            {
                "asset_type": "switch",
                "protocol": "ssh",
                "extra_args": {"category": "network"},
            }
        )
        with patch.object(session_inspector, "ssh_manager", fake):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertTrue(report["supported"])
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-network-cli-core-readonly")
        self.assertTrue(any("display version" in command for command in fake.commands))

    def test_snmp_inspection_prefers_configured_v3_auth_user(self):
        from core import session_inspector

        fake = FakeSSHManager(
            {
                "asset_type": "snmp",
                "protocol": "snmp",
                "host": "192.168.46.30",
                "port": 161,
                "username": "root",
                "extra_args": {
                    "snmp_version": "v3",
                    "v3_auth_user": "snmp-reader",
                    "v3_auth_pass": "auth-secret",
                },
            }
        )
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch("connections.snmp_manager.snmp_executor.get") as snmp_get,
        ):
            snmp_get.return_value = {"success": True, "data": []}
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        passed_args = snmp_get.call_args.kwargs["extra_args"]
        self.assertEqual(passed_args["v3_username"], "snmp-reader")
        self.assertNotEqual(passed_args["v3_username"], "root")


if __name__ == "__main__":
    unittest.main()
