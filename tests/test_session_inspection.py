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
        self.assertGreaterEqual(execute_command.call_count, 6)
        commands = [call.kwargs["command"] for call in execute_command.call_args_list]
        self.assertTrue(any("LogName='Security'" in command for command in commands))

    def test_hyperv_session_runs_hyperv_template_over_winrm(self):
        from core import session_inspector

        fake = FakeSSHManager(
            {
                "asset_type": "hyperv",
                "protocol": "winrm",
                "host": "hyperv.local",
                "port": 5985,
                "username": "admin",
                "password": "secret",
                "extra_args": {"category": "virtualization"},
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
        self.assertEqual(report["template_id"], "builtin-hyperv-core-readonly")
        commands = [call.kwargs["command"] for call in execute_command.call_args_list]
        self.assertTrue(any("Get-VMHost" in command for command in commands))
        self.assertTrue(any("Get-VM " in command for command in commands))

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

    def test_ceph_session_runs_storage_inspection_template(self):
        from core import session_inspector

        fake = FakeSSHManager(
            {
                "asset_type": "ceph",
                "protocol": "ssh",
                "extra_args": {"category": "storage"},
            }
        )
        with patch.object(session_inspector, "ssh_manager", fake):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertTrue(report["supported"])
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-ceph-core-readonly")
        self.assertTrue(any(command == "ceph status" for command in fake.commands))
        self.assertTrue(any(command == "ceph health detail" for command in fake.commands))

    def test_storage_ssh_assets_have_dedicated_inspection_templates(self):
        from core import session_inspector

        expected = {
            "nfs": "builtin-nfs-core-readonly",
            "hdfs": "builtin-hdfs-core-readonly",
            "glusterfs": "builtin-glusterfs-core-readonly",
        }
        for asset_type, template_id in expected.items():
            fake = FakeSSHManager(
                {
                    "asset_type": asset_type,
                    "protocol": "ssh",
                    "extra_args": {"category": "storage"},
                }
            )
            with self.subTest(asset_type=asset_type), patch.object(session_inspector, "ssh_manager", fake):
                report = asyncio.run(session_inspector.inspect_session("sid"))

            self.assertEqual(report["status"], "success")
            self.assertTrue(report["supported"])
            self.assertEqual(report["profile"], "template")
            self.assertEqual(report["template_id"], template_id)
            self.assertTrue(fake.commands)

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

    def test_s3_session_runs_object_storage_inspection(self):
        from core import session_inspector
        from connections import object_storage_manager

        fake = FakeSSHManager(
            {
                "asset_type": "s3",
                "protocol": "http_api",
                "host": "s3.local",
                "port": 443,
                "username": "ak",
                "password": "sk",
                "extra_args": {"bucket": "ops-logs"},
            }
        )

        class FakeObjectStorageExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "output": kwargs["operation"]}

        fake_executor = FakeObjectStorageExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(object_storage_manager, "object_storage_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-object-storage-core-readonly")
        self.assertIn("list_buckets", {call["operation"] for call in fake_executor.calls})
        self.assertIn("list_objects", {call["operation"] for call in fake_executor.calls})
        self.assertEqual({call["bucket"] for call in fake_executor.calls}, {None})

    def test_backup_session_runs_storage_platform_inspection(self):
        from core import session_inspector
        from connections import storage_platform_manager

        fake = FakeSSHManager(
            {
                "asset_type": "backup",
                "protocol": "backup",
                "host": "backup.local",
                "port": 443,
                "username": "ops",
                "password": "secret",
                "extra_args": {"jobs_path": "/api/jobs"},
            }
        )

        class FakeStoragePlatformExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "operation": kwargs["operation"], "output": kwargs["operation"]}

        fake_executor = FakeStoragePlatformExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(storage_platform_manager, "storage_platform_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-backup-storage-core-readonly")
        self.assertEqual(
            {call["operation"] for call in fake_executor.calls},
            {"health", "jobs", "repositories", "policies", "capacity"},
        )

    def test_memcached_session_runs_read_only_template(self):
        from core import session_inspector
        from connections import datastore_manager

        fake = FakeSSHManager(
            {
                "asset_type": "memcached",
                "protocol": "memcached",
                "host": "cache.local",
                "port": 11211,
                "extra_args": {},
            }
        )

        class FakeMemcachedExecutor:
            def __init__(self):
                self.commands = []

            def execute_command(self, **kwargs):
                self.commands.append(kwargs["command"])
                return {"success": True, "output": kwargs["command"]}

        fake_executor = FakeMemcachedExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(datastore_manager, "memcached_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-memcached-core-readonly")
        self.assertEqual(set(fake_executor.commands), {"version", "stats"})

    def test_service_probe_session_uses_service_probe_executor(self):
        from core import session_inspector
        from connections import service_probe_manager

        fake = FakeSSHManager(
            {
                "asset_type": "port",
                "protocol": "tcp",
                "host": "svc.local",
                "port": 8080,
                "extra_args": {"category": "service"},
            }
        )

        class FakeServiceProbeExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "message": "tcp ok", "protocol": kwargs["protocol"]}

        fake_executor = FakeServiceProbeExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(service_probe_manager, "service_probe_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "service_probe")
        self.assertEqual(fake_executor.calls[0]["protocol"], "tcp")

    def test_proxmox_template_uses_virtualization_executor_operations(self):
        from core import session_inspector
        from connections import virtualization_manager

        fake = FakeSSHManager(
            {
                "asset_type": "proxmox",
                "protocol": "proxmox",
                "host": "pve.local",
                "port": 8006,
                "extra_args": {"category": "virtualization", "api_token": "secret"},
            }
        )

        class FakeVirtualizationExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "operation": kwargs.get("operation"), "output": "{}"}

        fake_executor = FakeVirtualizationExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(virtualization_manager, "virtualization_api_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-proxmox-core-readonly")
        self.assertEqual(
            {call["operation"] for call in fake_executor.calls},
            {"version", "nodes", "resources", "storage"},
        )

    def test_vmware_template_uses_virtualization_executor_operations(self):
        from core import session_inspector
        from connections import virtualization_manager

        fake = FakeSSHManager(
            {
                "asset_type": "vmware",
                "protocol": "vmware",
                "host": "vcenter.local",
                "port": 443,
                "extra_args": {"category": "virtualization", "vmware_session_id": "secret"},
            }
        )

        class FakeVirtualizationExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "operation": kwargs.get("operation"), "output": "{}"}

        fake_executor = FakeVirtualizationExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(virtualization_manager, "virtualization_api_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-vmware-core-readonly")
        self.assertEqual(
            {call["operation"] for call in fake_executor.calls},
            {"version", "hosts", "vms", "datastores"},
        )

    def test_openstack_template_uses_virtualization_executor_operations(self):
        from core import session_inspector
        from connections import virtualization_manager

        fake = FakeSSHManager(
            {
                "asset_type": "openstack",
                "protocol": "openstack",
                "host": "openstack.local",
                "port": 5000,
                "extra_args": {"category": "virtualization", "openstack_token": "secret"},
            }
        )

        class FakeVirtualizationExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "operation": kwargs.get("operation"), "output": "{}"}

        fake_executor = FakeVirtualizationExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(virtualization_manager, "virtualization_api_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-openstack-core-readonly")
        self.assertEqual(
            {call["operation"] for call in fake_executor.calls},
            {"version", "catalog", "servers", "hypervisors", "networks", "volumes"},
        )

    def test_zstack_template_uses_virtualization_executor_operations(self):
        from core import session_inspector
        from connections import virtualization_manager

        fake = FakeSSHManager(
            {
                "asset_type": "zstack",
                "protocol": "zstack",
                "host": "zstack.local",
                "port": 8080,
                "extra_args": {"category": "virtualization", "zstack_session_uuid": "secret"},
            }
        )

        class FakeVirtualizationExecutor:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return {"success": True, "operation": kwargs.get("operation"), "output": "{}"}

        fake_executor = FakeVirtualizationExecutor()
        with (
            patch.object(session_inspector, "ssh_manager", fake),
            patch.object(virtualization_manager, "virtualization_api_executor", fake_executor),
        ):
            report = asyncio.run(session_inspector.inspect_session("sid"))

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["profile"], "template")
        self.assertEqual(report["template_id"], "builtin-zstack-core-readonly")
        self.assertEqual(
            {call["operation"] for call in fake_executor.calls},
            {"management_nodes", "zones", "clusters", "hosts", "vms", "volumes", "l3_networks"},
        )


if __name__ == "__main__":
    unittest.main()
