import os
import unittest
from pathlib import Path
from unittest.mock import patch

from core.safety_policy import (
    check_approval_needed,
    check_hard_block,
    check_readonly_block,
    classify_linux_actions,
    classify_memcached_actions,
    classify_mongodb_actions,
    classify_network_actions,
    classify_redis_actions,
    classify_windows_actions,
    explain_policy_decision,
    get_safety_policy,
    save_safety_policy,
    validate_safety_policy,
)


class TestSafetyPolicy(unittest.TestCase):
    def policy_path(self, filename: str) -> str:
        return str(Path.cwd() / filename)

    def cleanup_policy_file(self, path: str):
        for candidate in (path, f"{path}.tmp"):
            if os.path.exists(candidate):
                os.remove(candidate)

    def test_default_policy_requires_approval_for_sql_write(self):
        path = self.policy_path("safety_policy_test_missing_1.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                needs_approval, reason = check_approval_needed(
                    "db_execute_query",
                    {"sql": "DROP TABLE users"},
                    {"allow_modifications": True},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(needs_approval)
        self.assertIn("数据库", reason)

    def test_oracle_alter_system_requires_approval_but_is_not_hard_blocked(self):
        path = self.policy_path("safety_policy_test_oracle_alter_system.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                args = {"sql": "ALTER SYSTEM SWITCH LOGFILE"}
                context = {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"}
                needs_approval, reason = check_approval_needed("db_execute_query", args, context)
                hard_blocked, _ = check_hard_block("db_execute_query", args, context)
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(needs_approval)
        self.assertIn("数据库实例级管理", reason)
        self.assertFalse(hard_blocked)

    def test_explain_policy_decision_returns_business_actions(self):
        result = explain_policy_decision(
            "db_execute_query",
            {"sql": "ALTER SYSTEM SWITCH LOGFILE"},
            {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"},
        )

        self.assertEqual(result["decision"], "approval")
        self.assertEqual(result["primary_action"]["id"], "sql.instance_admin")
        self.assertEqual(result["primary_action"]["label"], "数据库实例管理")
        self.assertIn("运行状态", result["primary_action"]["description"])
        self.assertEqual(result["resolution_layer"], "action_policy")
        self.assertTrue(any(layer["id"] == "action_policy" and layer["matched"] for layer in result["policy_layers"]))

    def test_default_policy_explains_sql_write_actions_in_plain_language(self):
        path = self.policy_path("safety_policy_test_sql_plain_language.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                data_write = check_approval_needed(
                    "db_execute_query",
                    {"sql": "UPDATE users SET status = 1 WHERE id = 1"},
                    {"allow_modifications": True},
                )
                schema_change = check_approval_needed(
                    "db_execute_query",
                    {"sql": "ALTER TABLE users ADD remark VARCHAR2(200)"},
                    {"allow_modifications": True},
                )
                readonly_block = check_readonly_block(
                    "db_execute_query",
                    {"sql": "GRANT SELECT ON app.orders TO readonly_user"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(data_write[0])
        self.assertIn("数据写入", data_write[1])
        self.assertTrue(schema_change[0])
        self.assertIn("结构", schema_change[1])
        self.assertTrue(readonly_block[0])
        self.assertIn("账号权限", readonly_block[1])

    def test_default_policy_hard_blocks_high_risk_database_administration(self):
        path = self.policy_path("safety_policy_test_missing_sql_hard_block.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                blocked, reason = check_hard_block(
                    "db_execute_query",
                    {"sql": "DROP USER app_user CASCADE"},
                    {"allow_modifications": True},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(blocked)
        self.assertIn("硬拦截", reason)

    def test_evolve_skill_requires_skill_change_approval(self):
        path = self.policy_path("safety_policy_test_missing_skill_change.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                needs_approval, reason = check_approval_needed(
                    "evolve_skill",
                    {
                        "skill_id": "linux-hardening",
                        "file_name": "SKILL.md",
                        "content": "---\nname: linux-hardening\n---\n",
                    },
                    {"allow_modifications": True},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(needs_approval)
        self.assertIn("技能", reason)

    def test_evolve_skill_path_traversal_is_hard_blocked(self):
        path = self.policy_path("safety_policy_test_missing_skill_block.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                from core.safety_policy import check_hard_block

                blocked, reason = check_hard_block(
                    "evolve_skill",
                    {
                        "skill_id": "../escape",
                        "file_name": "SKILL.md",
                    },
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(blocked)
        self.assertIn("硬拦截", reason)

    def test_default_policy_blocks_sql_write_in_readonly(self):
        path = self.policy_path("safety_policy_test_missing_2.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                blocked, reason = check_readonly_block(
                    "db_execute_query",
                    {"sql": "UPDATE users SET name='x'"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(blocked)
        self.assertIn("只读安全模式", reason)

    def test_default_policy_allows_readonly_linux_inspection_without_unknown_approval(self):
        path = self.policy_path("safety_policy_test_missing_3.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                needs_approval, _ = check_approval_needed(
                    "linux_execute_command",
                    {"command": "uname -a"},
                    {"allow_modifications": False},
                )
                blocked, _ = check_readonly_block(
                    "linux_execute_command",
                    {"command": "uname -a"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertFalse(needs_approval)
        self.assertFalse(blocked)

    def test_default_policy_allows_readonly_linux_log_queries_with_dev_null_redirects(self):
        path = self.policy_path("safety_policy_test_linux_readonly_dev_null.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                commands = [
                    'systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -40',
                    'journalctl -u sshd --no-pager -n 100 2>/dev/null | tail -50',
                    'cat /var/log/secure 2>/dev/null | grep "Failed password" | tail -20',
                    'ss -tulpn 2>&1 | head -30',
                ]
                decisions = [
                    (
                        check_approval_needed(
                            "linux_execute_command",
                            {"command": command},
                            {"allow_modifications": False},
                        ),
                        check_readonly_block(
                            "linux_execute_command",
                            {"command": command},
                            {"allow_modifications": False},
                        ),
                    )
                    for command in commands
                ]
        finally:
            self.cleanup_policy_file(path)

        for approval, readonly_block in decisions:
            self.assertFalse(approval[0], approval[1])
            self.assertFalse(readonly_block[0], readonly_block[1])

    def test_default_policy_allows_standard_linux_readonly_inspection_commands(self):
        path = self.policy_path("safety_policy_test_linux_readonly_inspection_commands.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                commands = [
                    "free -m",
                    "df -hT",
                    "lscpu",
                    'journalctl -p err --since "24 hours ago" --no-pager -n 100',
                    "crontab -l",
                    "systemctl list-units --state=failed --no-pager",
                    "last reboot",
                ]
                decisions = [
                    (
                        check_approval_needed(
                            "linux_execute_command",
                            {"command": command},
                            {"allow_modifications": False},
                        ),
                        check_readonly_block(
                            "linux_execute_command",
                            {"command": command},
                            {"allow_modifications": False},
                        ),
                    )
                    for command in commands
                ]
        finally:
            self.cleanup_policy_file(path)

        for approval, readonly_block in decisions:
            self.assertFalse(approval[0], approval[1])
            self.assertFalse(readonly_block[0], readonly_block[1])

    def test_default_policy_still_blocks_linux_file_writes_and_service_changes(self):
        path = self.policy_path("safety_policy_test_linux_readonly_writes.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                file_write_blocked = check_readonly_block(
                    "linux_execute_command",
                    {"command": "journalctl -xe > /tmp/journal.txt"},
                    {"allow_modifications": False},
                )
                service_restart_blocked = check_readonly_block(
                    "linux_execute_command",
                    {"command": "systemctl restart sshd 2>/dev/null"},
                    {"allow_modifications": False},
                )
                reboot_blocked = check_readonly_block(
                    "linux_execute_command",
                    {"command": "sudo reboot"},
                    {"allow_modifications": False},
                )
                shutdown_blocked = check_readonly_block(
                    "linux_execute_command",
                    {"command": "last reboot; /sbin/shutdown -h now"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(file_write_blocked[0])
        self.assertTrue(service_restart_blocked[0])
        self.assertTrue(reboot_blocked[0])
        self.assertTrue(shutdown_blocked[0])

    def test_linux_action_classifier_distinguishes_read_history_from_reboot(self):
        self.assertIn("linux.read.history", classify_linux_actions("last reboot"))
        self.assertNotIn("linux.system.power", classify_linux_actions("last reboot"))
        self.assertIn("linux.system.power", classify_linux_actions("sudo reboot"))
        self.assertIn("linux.read.service", classify_linux_actions("systemctl status sshd --no-pager"))
        self.assertIn("linux.service.change", classify_linux_actions("systemctl restart sshd"))

    def test_linux_action_classifier_distinguishes_network_read_from_change(self):
        self.assertIn("linux.read.network", classify_linux_actions("ip route show"))
        self.assertNotIn("linux.network.change", classify_linux_actions("ip route show"))
        self.assertIn("linux.network.change", classify_linux_actions("ip route add 10.0.0.0/24 via 172.17.10.1"))
        self.assertIn("linux.network.change", classify_linux_actions("route add default gw 172.17.10.1"))
        self.assertIn("linux.read.network", classify_linux_actions("firewall-cmd --list-all"))
        self.assertIn("linux.network.change", classify_linux_actions("firewall-cmd --add-port=1521/tcp"))

    def test_linux_action_classifier_distinguishes_filesystem_reads_from_mount_changes(self):
        readonly_commands = [
            "mount",
            "mount -l",
            "findmnt -no OPTIONS /tmp",
            "lsblk -f",
            "blkid",
            "cat /etc/fstab",
            "cat /sys/block/vda/queue/scheduler",
        ]
        for command in readonly_commands:
            with self.subTest(command=command):
                actions = classify_linux_actions(command)
                self.assertIn("linux.read.filesystem", actions)
                self.assertNotIn("linux.disk.change", actions)

        self.assertIn("linux.disk.change", classify_linux_actions("mount /dev/sdb1 /mnt/data"))
        self.assertIn("linux.disk.change", classify_linux_actions("umount /mnt/data"))
        self.assertIn("linux.disk.change", classify_linux_actions("swapon /swapfile"))

    def test_default_policy_allows_readonly_filesystem_queries(self):
        path = self.policy_path("safety_policy_test_linux_filesystem_read_allow.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["linux"]["approval_patterns"].append(r"\bmount\b")
                save_safety_policy(policy)
                for command in (
                    "mount",
                    "cat /etc/fstab",
                    "cat /sys/block/vda/queue/scheduler",
                    "findmnt -no OPTIONS /tmp",
                ):
                    with self.subTest(command=command):
                        result = explain_policy_decision(
                            "linux_execute_command",
                            {"command": command},
                            {"allow_modifications": False, "asset_type": "linux", "protocol": "ssh"},
                        )
                        self.assertEqual(result["decision"], "allow")
                        self.assertEqual(result["primary_action"]["id"], "linux.read.filesystem")
        finally:
            self.cleanup_policy_file(path)

    def test_linux_action_rules_can_allow_readonly_without_regex_changes(self):
        path = self.policy_path("safety_policy_test_linux_action_rules_allow.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["linux"]["readonly_block_patterns"].append(r"\breboot\b")
                policy["action_rules"]["linux"]["linux.read.history"] = "allow"
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "last reboot"},
                    {"allow_modifications": False, "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["primary_action"]["id"], "linux.read.history")

    def test_linux_action_allow_overrides_legacy_approval_pattern(self):
        path = self.policy_path("safety_policy_test_linux_action_rules_approval_override.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["linux"]["approval_patterns"].append(r"\bfirewall-cmd\b")
                policy["action_rules"]["linux"]["linux.read.network"] = "allow"
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "firewall-cmd --list-all"},
                    {"allow_modifications": False, "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["primary_action"]["id"], "linux.read.network")

    def test_linux_action_rules_support_approval_without_command_regex(self):
        path = self.policy_path("safety_policy_test_linux_action_rules_approval.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["linux"]["approval_patterns"] = []
                policy["categories"]["linux"]["readonly_block_patterns"] = []
                policy["action_rules"]["linux"]["linux.service.change"] = "approval"
                save_safety_policy(policy)
                readwrite = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": True, "asset_type": "linux", "protocol": "ssh"},
                )
                readonly = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": False, "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(readwrite["decision"], "approval")
        self.assertEqual(readonly["decision"], "readonly_block")
        self.assertEqual(readwrite["primary_action"]["id"], "linux.service.change")

    def test_windows_action_classifier_preserves_readonly_powershell(self):
        service_query = "Get-Service | Where-Object {$_.Status -ne 'Running'} | Select-Object Name,Status"
        event_query = "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-1)}"
        self.assertIn("windows.read.service", classify_windows_actions(service_query))
        self.assertNotIn("windows.service.change", classify_windows_actions(service_query))
        self.assertIn("windows.read.eventlog", classify_windows_actions(event_query))
        self.assertNotIn("windows.registry.change", classify_windows_actions(event_query))

    def test_windows_action_classifier_detects_changes(self):
        self.assertIn("windows.service.change", classify_windows_actions("Restart-Service Spooler"))
        self.assertIn("windows.system.power", classify_windows_actions("Restart-Computer -Force"))
        self.assertIn("windows.registry.change", classify_windows_actions("Set-ItemProperty HKLM:\\Software\\Ops Name Value"))
        self.assertIn("windows.firewall.change", classify_windows_actions("New-NetFirewallRule -DisplayName Ops -Action Allow"))
        self.assertIn("hyperv.vm.delete", classify_windows_actions("Remove-VM -Name old-vm -Force"))

    def test_windows_action_allow_overrides_legacy_pattern_for_readonly(self):
        path = self.policy_path("safety_policy_test_windows_action_read_allow.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["windows"]["approval_patterns"].append(r"\bGet-WinEvent\b")
                policy["action_rules"]["windows"]["windows.read.eventlog"] = "allow"
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "winrm_execute_command",
                    {"command": "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2} -MaxEvents 20"},
                    {"allow_modifications": False, "asset_type": "windows", "protocol": "winrm"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["primary_action"]["id"], "windows.read.eventlog")

    def test_windows_action_allow_overrides_legacy_hard_block_for_readonly(self):
        path = self.policy_path("safety_policy_test_windows_action_hard_allow.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["windows"]["hard_block_substrings"].append("format")
                policy["action_rules"]["windows"]["windows.read.eventlog"] = "allow"
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "winrm_execute_command",
                    {"command": "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2} -MaxEvents 20 | Format-Table -AutoSize"},
                    {"allow_modifications": False, "asset_type": "windows", "protocol": "winrm"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["primary_action"]["id"], "windows.read.eventlog")

    def test_windows_action_rules_support_approval_without_command_regex(self):
        path = self.policy_path("safety_policy_test_windows_action_approval.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["windows"]["approval_patterns"] = []
                policy["categories"]["windows"]["readonly_block_patterns"] = []
                policy["action_rules"]["windows"]["windows.service.change"] = "approval"
                save_safety_policy(policy)
                readwrite = explain_policy_decision(
                    "winrm_execute_command",
                    {"command": "Restart-Service Spooler"},
                    {"allow_modifications": True, "asset_type": "windows", "protocol": "winrm"},
                )
                readonly = explain_policy_decision(
                    "winrm_execute_command",
                    {"command": "Restart-Service Spooler"},
                    {"allow_modifications": False, "asset_type": "windows", "protocol": "winrm"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(readwrite["decision"], "approval")
        self.assertEqual(readonly["decision"], "readonly_block")
        self.assertEqual(readwrite["primary_action"]["id"], "windows.service.change")

    def test_network_boundary_blocks_windows_active_probe_outside_allowed_cidr(self):
        path = self.policy_path("safety_policy_test_windows_network_boundary.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["network_boundary"] = {
                    "enabled": True,
                    "active_cidrs": ["172.17.0.0/16"],
                    "readonly_cidrs": [],
                    "blocked_cidrs": [],
                    "allowed_hosts": ["win.local"],
                    "blocked_hosts": [],
                    "block_unknown_targets": True,
                }
                save_safety_policy(policy)
                blocked, reason = check_hard_block(
                    "winrm_execute_command",
                    {"command": "Test-NetConnection 8.8.8.8 -Port 443"},
                    {"host": "win.local", "allow_modifications": False, "asset_type": "windows", "protocol": "winrm"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(blocked)
        self.assertIn("8.8.8.8", reason)

    def test_network_action_classifier_distinguishes_reads_and_changes(self):
        status_actions = classify_network_actions("display interface brief")
        self.assertIn("network.read.status", status_actions)
        self.assertNotIn("network.interface.change", status_actions)
        self.assertEqual(classify_network_actions("display current-configuration"), ["network.read.config"])
        self.assertEqual(classify_network_actions("display cu"), ["network.read.config"])
        self.assertEqual(classify_network_actions("show run"), ["network.read.config"])
        self.assertIn("network.config.mode", classify_network_actions("system-view"))
        self.assertIn("network.interface.change", classify_network_actions("interface GigabitEthernet0/0/1\nshutdown"))
        self.assertIn("network.route.change", classify_network_actions("ip route-static 10.0.0.0 255.255.255.0 172.17.1.1"))
        self.assertIn("network.acl_nat.change", classify_network_actions("acl 3000"))
        self.assertIn("network.save_config", classify_network_actions("write memory"))
        self.assertIn("network.file_transfer", classify_network_actions("copy tftp flash"))
        self.assertIn("network.reset", classify_network_actions("reset saved-configuration"))

    def test_network_action_rules_drive_decision_and_override_legacy_patterns(self):
        path = self.policy_path("safety_policy_test_network_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["network"]["approval_patterns"].append(r"\binterface\b")
                save_safety_policy(policy)
                status = explain_policy_decision(
                    "network_cli_execute_command",
                    {"command": "display interface brief"},
                    {"allow_modifications": False, "asset_type": "switch", "protocol": "ssh"},
                )
                config = explain_policy_decision(
                    "network_cli_execute_command",
                    {"command": "display current-configuration"},
                    {"allow_modifications": True, "asset_type": "switch", "protocol": "ssh"},
                )
                reset = explain_policy_decision(
                    "network_cli_execute_command",
                    {"command": "reset saved-configuration"},
                    {"allow_modifications": True, "asset_type": "switch", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(status["decision"], "allow")
        self.assertEqual(status["primary_action"]["id"], "network.read.status")
        self.assertEqual(config["decision"], "approval")
        self.assertEqual(config["primary_action"]["id"], "network.read.config")
        self.assertEqual(reset["decision"], "deny")
        self.assertEqual(reset["primary_action"]["id"], "network.reset")

    def test_network_boundary_blocks_network_device_diagnostic_outside_allowed_cidr(self):
        path = self.policy_path("safety_policy_test_network_device_boundary.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["network_boundary"] = {
                    "enabled": True,
                    "active_cidrs": ["172.17.0.0/16"],
                    "readonly_cidrs": [],
                    "blocked_cidrs": [],
                    "allowed_hosts": [],
                    "blocked_hosts": [],
                    "block_unknown_targets": True,
                }
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "network_cli_execute_command",
                    {"command": "ping 8.8.8.8"},
                    {"allow_modifications": True, "host": "172.17.10.1", "asset_type": "switch", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertEqual(result["resolution_layer"], "network_boundary")
        self.assertIn("8.8.8.8", result["reason"])

    def test_redis_action_classifier_distinguishes_reads_and_writes(self):
        self.assertEqual(classify_redis_actions("INFO"), ["redis.read"])
        self.assertEqual(classify_redis_actions("GET app:key"), ["redis.read"])
        self.assertEqual(classify_redis_actions("SET app:key value"), ["redis.key_write"])
        self.assertEqual(classify_redis_actions("DEL app:key"), ["redis.key_delete"])
        self.assertEqual(classify_redis_actions("EXPIRE app:key 60"), ["redis.expire"])
        self.assertEqual(classify_redis_actions("CONFIG SET maxmemory 1gb"), ["redis.config_change"])
        self.assertEqual(classify_redis_actions("FLUSHALL"), ["redis.flush"])

    def test_redis_action_rules_drive_decision(self):
        path = self.policy_path("safety_policy_test_redis_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["redis"]["approval_commands"] = []
                policy["categories"]["redis"]["readonly_block_commands"] = []
                save_safety_policy(policy)
                read = explain_policy_decision(
                    "redis_execute_command",
                    {"command": "INFO"},
                    {"allow_modifications": False, "asset_type": "redis", "protocol": "redis"},
                )
                write = explain_policy_decision(
                    "redis_execute_command",
                    {"command": "SET app:key value"},
                    {"allow_modifications": True, "asset_type": "redis", "protocol": "redis"},
                )
                flush = explain_policy_decision(
                    "redis_execute_command",
                    {"command": "FLUSHALL"},
                    {"allow_modifications": True, "asset_type": "redis", "protocol": "redis"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(read["decision"], "allow")
        self.assertEqual(read["primary_action"]["id"], "redis.read")
        self.assertEqual(write["decision"], "approval")
        self.assertEqual(write["primary_action"]["id"], "redis.key_write")
        self.assertEqual(flush["decision"], "deny")
        self.assertEqual(flush["primary_action"]["id"], "redis.flush")

    def test_memcached_action_classifier_distinguishes_reads_and_writes(self):
        self.assertEqual(classify_memcached_actions("version"), ["memcached.read"])
        self.assertEqual(classify_memcached_actions("stats"), ["memcached.read"])
        self.assertEqual(classify_memcached_actions("get app:key"), ["memcached.read"])
        self.assertEqual(classify_memcached_actions("set app:key 0 60 5"), ["memcached.key_write"])
        self.assertEqual(classify_memcached_actions("delete app:key"), ["memcached.key_delete"])
        self.assertEqual(classify_memcached_actions("incr counter 1"), ["memcached.counter_change"])
        self.assertEqual(classify_memcached_actions("flush_all"), ["memcached.flush"])

    def test_memcached_action_rules_drive_decision(self):
        path = self.policy_path("safety_policy_test_memcached_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["memcached"]["approval_commands"] = []
                policy["categories"]["memcached"]["readonly_block_commands"] = []
                save_safety_policy(policy)
                read = explain_policy_decision(
                    "memcached_execute_command",
                    {"command": "stats"},
                    {"allow_modifications": False, "asset_type": "memcached", "protocol": "memcached"},
                )
                write = explain_policy_decision(
                    "memcached_execute_command",
                    {"command": "set app:key 0 60 5"},
                    {"allow_modifications": True, "asset_type": "memcached", "protocol": "memcached"},
                )
                flush = explain_policy_decision(
                    "memcached_execute_command",
                    {"command": "flush_all"},
                    {"allow_modifications": True, "asset_type": "memcached", "protocol": "memcached"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(read["decision"], "allow")
        self.assertEqual(read["primary_action"]["id"], "memcached.read")
        self.assertEqual(write["decision"], "approval")
        self.assertEqual(write["primary_action"]["id"], "memcached.key_write")
        self.assertEqual(flush["decision"], "deny")
        self.assertEqual(flush["primary_action"]["id"], "memcached.flush")

    def test_mongodb_action_classifier_distinguishes_reads_and_risky_operations(self):
        self.assertEqual(classify_mongodb_actions(operation="find"), ["mongodb.find"])
        self.assertEqual(classify_mongodb_actions(operation="aggregate"), ["mongodb.aggregate"])
        self.assertEqual(classify_mongodb_actions(operation="updateOne"), ["mongodb.write"])
        self.assertEqual(classify_mongodb_actions(operation="createIndex"), ["mongodb.index_change"])
        self.assertEqual(classify_mongodb_actions(operation="createUser"), ["mongodb.admin"])
        self.assertEqual(classify_mongodb_actions(operation="dropDatabase"), ["mongodb.drop"])

    def test_mongodb_find_action_is_allow_and_available_to_policy_preview(self):
        path = self.policy_path("safety_policy_test_mongodb_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                result = explain_policy_decision(
                    "mongodb_find",
                    {"operation": "find", "command": "db.orders.find({}).limit(20)"},
                    {"allow_modifications": False, "asset_type": "mongodb", "protocol": "mongodb"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["primary_action"]["id"], "mongodb.find")

    def test_network_boundary_blocks_active_probe_outside_allowed_cidr(self):
        path = self.policy_path("safety_policy_test_network_boundary.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["network_boundary"] = {
                    "enabled": True,
                    "active_cidrs": ["172.17.0.0/16"],
                    "readonly_cidrs": ["10.0.0.0/8"],
                    "blocked_cidrs": [],
                    "allowed_hosts": [],
                    "blocked_hosts": [],
                    "block_unknown_targets": True,
                }
                save_safety_policy(policy)
                allowed = check_hard_block(
                    "linux_execute_command",
                    {"command": "ping -c 1 172.17.8.150"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
                readonly_blocked = check_hard_block(
                    "linux_execute_command",
                    {"command": "curl http://10.39.80.238:9100/metrics"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
                unknown_blocked = check_hard_block(
                    "linux_execute_command",
                    {"command": "nc -vz 192.168.1.10 22"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
                hostname_blocked = check_hard_block(
                    "linux_execute_command",
                    {"command": "ping example.com"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertFalse(allowed[0])
        self.assertTrue(readonly_blocked[0])
        self.assertIn("只允许读取已有平台数据", readonly_blocked[1])
        self.assertTrue(unknown_blocked[0])
        self.assertTrue(hostname_blocked[0])

    def test_network_boundary_blocks_http_get_outside_allowed_targets(self):
        path = self.policy_path("safety_policy_test_network_boundary_http_get.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["network_boundary"] = {
                    "enabled": True,
                    "active_cidrs": ["172.17.0.0/16"],
                    "readonly_cidrs": [],
                    "blocked_cidrs": [],
                    "allowed_hosts": [],
                    "blocked_hosts": [],
                    "block_unknown_targets": True,
                }
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "http_api_request",
                    {"method": "GET", "url": "http://203.0.113.10/api/health"},
                    {"allow_modifications": False, "asset_type": "http_api", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertEqual(result["resolution_layer"], "network_boundary")

    def test_network_boundary_ignores_network_command_option_values(self):
        path = self.policy_path("safety_policy_test_network_boundary_command_options.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["network_boundary"] = {
                    "enabled": True,
                    "active_cidrs": ["172.17.0.0/16"],
                    "readonly_cidrs": [],
                    "blocked_cidrs": [],
                    "allowed_hosts": [],
                    "blocked_hosts": [],
                    "block_unknown_targets": True,
                }
                save_safety_policy(policy)
                curl_allowed = check_hard_block(
                    "linux_execute_command",
                    {"command": "curl -X GET -H 'Accept: application/json' http://172.17.8.150/api/health"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
                scp_allowed = check_hard_block(
                    "linux_execute_command",
                    {"command": "scp file.txt root@172.17.8.150:/tmp/file.txt"},
                    {"allow_modifications": False, "host": "172.17.8.150", "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertFalse(curl_allowed[0])
        self.assertFalse(scp_allowed[0])

    def test_default_policy_allows_readonly_windows_new_object_inspection(self):
        path = self.policy_path("safety_policy_test_missing_4.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                command = "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,LastBootUpTime"
                needs_approval, _ = check_approval_needed(
                    "winrm_execute_command",
                    {"command": command},
                    {"allow_modifications": False},
                )
                blocked, _ = check_readonly_block(
                    "winrm_execute_command",
                    {"command": command},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertFalse(needs_approval)
        self.assertFalse(blocked)

    def test_default_policy_allows_network_display_but_blocks_config(self):
        path = self.policy_path("safety_policy_test_missing_5.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                display_needs_approval, _ = check_approval_needed(
                    "network_cli_execute_command",
                    {"command": "display version"},
                    {"allow_modifications": False},
                )
                display_blocked, _ = check_readonly_block(
                    "network_cli_execute_command",
                    {"command": "display version"},
                    {"allow_modifications": False},
                )
                config_blocked, _ = check_readonly_block(
                    "network_cli_execute_command",
                    {"command": "system-view\ninterface GigabitEthernet1/0/1"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertFalse(display_needs_approval)
        self.assertFalse(display_blocked)
        self.assertTrue(config_blocked)

    def test_hard_block_applies_to_linux_and_network_tools(self):
        path = self.policy_path("safety_policy_test_missing_6.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                from core.safety_policy import check_hard_block

                linux_blocked, linux_reason = check_hard_block(
                    "linux_execute_command",
                    {"command": "rm -rf /"},
                )
                network_blocked, network_reason = check_hard_block(
                    "network_cli_execute_command",
                    {"command": "reset saved-configuration"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(linux_blocked)
        self.assertIn("硬拦截", linux_reason)
        self.assertTrue(network_blocked)
        self.assertIn("硬拦截", network_reason)

    def test_hard_block_substrings_apply_to_http_policy_text(self):
        path = self.policy_path("safety_policy_test_http_hard_block_text.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["http"]["hard_block_substrings"] = ["publicaccessblock"]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "storage_api_request",
                    {"method": "PUT", "path": "/bucket?publicAccessBlock"},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "s3"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertEqual(result["resolution_layer"], "advanced_deny")

    def test_policy_can_be_customized_and_persisted(self):
        path = self.policy_path("safety_policy_test_tmp.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["categories"]["redis"]["readonly_block_commands"] = ["get"]
                save_safety_policy(policy)
                blocked, _ = check_readonly_block(
                    "redis_execute_command",
                    {"command": "GET foo"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(blocked)

    def test_explain_policy_decision_previews_hard_block_without_execution(self):
        path = self.policy_path("safety_policy_test_explain_hard.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "rm -rf /"},
                    {"allow_modifications": True},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertEqual(result["label"], "禁止执行")
        self.assertTrue(result["checks"][0]["matched"])

    def test_explain_policy_decision_marks_readonly_change_as_block(self):
        path = self.policy_path("safety_policy_test_explain_approval.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "readonly_block")
        self.assertIn("只读安全模式", result["reason"])

    def test_explain_policy_decision_allows_safe_readonly_command(self):
        path = self.policy_path("safety_policy_test_explain_allow.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "uname -a"},
                    {"allow_modifications": False},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")

    def test_semantic_rule_can_require_approval(self):
        path = self.policy_path("safety_policy_test_semantic_approval.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "restart-nginx",
                        "name": "重启 Nginx 需要审批",
                        "domain": "os",
                        "platform": "Linux",
                        "category": "linux",
                        "decision": "approval",
                        "enabled": True,
                        "matchers": [{"type": "command_prefix", "value": "systemctl restart nginx"}],
                    }
                ]
                save_safety_policy(policy)
                needs_approval, reason = check_approval_needed(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": True, "asset_type": "ssh", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(needs_approval)
        self.assertIn("重启 Nginx", reason)

    def test_disabled_semantic_rule_is_ignored(self):
        path = self.policy_path("safety_policy_test_semantic_disabled.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "disabled-deny",
                        "name": "停用的禁止规则",
                        "domain": "os",
                        "platform": "Linux",
                        "category": "linux",
                        "decision": "deny",
                        "enabled": False,
                        "matchers": [{"type": "contains", "value": "uname"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "uname -a"},
                    {"allow_modifications": False, "asset_type": "linux"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")

    def test_semantic_deny_rule_overrides_legacy_allow(self):
        path = self.policy_path("safety_policy_test_semantic_deny.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "deny-public-bucket",
                        "name": "禁止公开 Bucket",
                        "domain": "storage",
                        "platform": "S3",
                        "category": "http",
                        "decision": "deny",
                        "enabled": True,
                        "matchers": [{"type": "api_path_contains", "value": "publicAccessBlock"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "storage_api_request",
                    {"method": "PUT", "path": "/bucket?publicAccessBlock"},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertIn("禁止公开 Bucket", result["reason"])
        self.assertEqual(result["resolution_layer"], "advanced_deny")

    def test_domain_http_tools_share_http_method_policy(self):
        path = self.policy_path("safety_policy_test_domain_http_methods.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                needs_approval, approval_reason = check_approval_needed(
                    "bigdata_api_request",
                    {"method": "POST", "path": "/api/v1/dags/reload"},
                    {"allow_modifications": True, "asset_type": "airflow", "protocol": "http_api"},
                )
                blocked, block_reason = check_readonly_block(
                    "bigdata_api_request",
                    {"method": "DELETE", "path": "/api/v1/dags/old"},
                    {"allow_modifications": False, "asset_type": "airflow", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertTrue(needs_approval)
        self.assertIn("HTTP POST", approval_reason)
        self.assertTrue(blocked)
        self.assertIn("HTTP DELETE", block_reason)

    def test_s3_operation_semantics_can_be_configured_without_regex_path(self):
        path = self.policy_path("safety_policy_test_s3_operation.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "deny-delete-object",
                        "name": "禁止删除对象",
                        "domain": "storage",
                        "platform": "S3",
                        "category": "http",
                        "decision": "deny",
                        "enabled": True,
                        "matchers": [{"type": "contains", "value": "delete_object"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "storage_api_request",
                    {"operation": "delete_object", "bucket": "ops", "key": "a.log"},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertIn("禁止删除对象", result["reason"])

    def test_platform_action_rules_can_be_customized_by_action_id(self):
        path = self.policy_path("safety_policy_test_platform_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["action_rules"]["http"] = {"s3.download_object": "approval"}
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "storage_api_request",
                    {"operation": "download_object", "bucket": "ops", "key": "a.log"},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "s3"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "approval")
        self.assertEqual(result["primary_action"]["id"], "s3.download_object")
        self.assertEqual(result["resolution_layer"], "action_policy")

    def test_default_platform_action_rules_cover_high_risk_s3_actions(self):
        path = self.policy_path("safety_policy_test_default_s3_action_rules.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                delete_bucket = explain_policy_decision(
                    "storage_api_request",
                    {"method": "DELETE", "path": "/prod-bucket"},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "s3"},
                )
                publish_bucket = explain_policy_decision(
                    "storage_api_request",
                    {"method": "PUT", "path": "/prod-bucket?publicAccessBlock", "body": {"public": True}},
                    {"allow_modifications": True, "asset_type": "s3", "protocol": "s3"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(delete_bucket["decision"], "deny")
        self.assertEqual(delete_bucket["resolution_layer"], "action_policy")
        self.assertEqual(publish_bucket["decision"], "deny")
        self.assertEqual(publish_bucket["resolution_layer"], "action_policy")

    def test_action_allow_overrides_legacy_semantic_approval_fallback(self):
        path = self.policy_path("safety_policy_test_action_allow_overrides_semantic_approval.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "legacy-network-approval",
                        "name": "旧审批规则",
                        "category": "linux",
                        "decision": "approval",
                        "enabled": True,
                        "matchers": [{"type": "linux_action", "value": "linux.read.network"}],
                    }
                ]
                policy["action_rules"]["linux"]["linux.read.network"] = "allow"
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "ss -tulpn"},
                    {"allow_modifications": False, "asset_type": "linux", "protocol": "ssh"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["resolution_layer"], "action_policy")

    def test_memcached_write_command_is_blocked_in_readonly(self):
        result = explain_policy_decision(
            "memcached_execute_command",
            {"command": "flush_all"},
            {"allow_modifications": False, "asset_type": "memcached", "protocol": "memcached"},
        )

        self.assertEqual(result["decision"], "deny")
        self.assertIn("拦截", result["reason"])

    def test_semantic_rule_scope_limits_by_tag(self):
        path = self.policy_path("safety_policy_test_semantic_scope.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "prod-restart",
                        "name": "生产环境重启服务需要审批",
                        "domain": "os",
                        "platform": "Linux",
                        "category": "linux",
                        "decision": "approval",
                        "scope": {"type": "tag", "value": "生产"},
                        "matchers": [{"type": "command_prefix", "value": "systemctl restart"}],
                    }
                ]
                save_safety_policy(policy)
                test_args = {"command": "systemctl restart nginx"}
                dev_result = explain_policy_decision(
                    "linux_execute_command",
                    test_args,
                    {"allow_modifications": True, "asset_type": "ssh", "tags": ["测试"]},
                )
                prod_result = explain_policy_decision(
                    "linux_execute_command",
                    test_args,
                    {"allow_modifications": True, "asset_type": "ssh", "tags": ["生产"]},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(dev_result["decision"], "approval")  # legacy default still catches restart
        self.assertNotIn("生产环境", dev_result["reason"])
        self.assertEqual(prod_result["decision"], "approval")
        self.assertIn("生产环境", prod_result["reason"])

    def test_scoped_semantic_deny_uses_context(self):
        path = self.policy_path("safety_policy_test_scoped_deny_context.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "prod-deny-reboot",
                        "name": "生产禁止重启",
                        "domain": "os",
                        "platform": "Linux",
                        "category": "linux",
                        "decision": "deny",
                        "scope": {"type": "tag", "value": "生产"},
                        "matchers": [{"type": "command_prefix", "value": "reboot"}],
                    }
                ]
                save_safety_policy(policy)
                dev_result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "reboot"},
                    {"allow_modifications": True, "asset_type": "ssh", "tags": ["测试"]},
                )
                prod_result = explain_policy_decision(
                    "linux_execute_command",
                    {"command": "reboot"},
                    {"allow_modifications": True, "asset_type": "ssh", "tags": ["生产"]},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertNotEqual(dev_result["decision"], "deny")
        self.assertEqual(prod_result["decision"], "deny")

    def test_semantic_platform_action_matches_k8s_namespace_delete(self):
        path = self.policy_path("safety_policy_test_platform_action.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "deny-k8s-ns-delete",
                        "name": "禁止删除 Kubernetes Namespace",
                        "domain": "cloudnative",
                        "platform": "Kubernetes",
                        "category": "http",
                        "decision": "deny",
                        "matchers": [{"type": "platform_action", "value": "k8s.delete_namespace"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "k8s_api_request",
                    {"method": "DELETE", "path": "/api/v1/namespaces/prod"},
                    {"allow_modifications": True, "asset_type": "k8s", "protocol": "k8s"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertIn("Namespace", result["reason"])

    def test_semantic_sql_action_matches_oracle_instance_admin_without_regex(self):
        path = self.policy_path("safety_policy_test_sql_action.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "oracle-instance-admin",
                        "name": "数据库实例管理需要审批",
                        "domain": "database",
                        "platform": "Oracle",
                        "category": "sql",
                        "decision": "approval",
                        "matchers": [{"type": "sql_action", "value": "sql.instance_admin"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "db_execute_query",
                    {"sql": "ALTER SYSTEM SWITCH LOGFILE"},
                    {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "approval")
        self.assertIn("数据库实例管理", result["reason"])

    def test_semantic_sql_action_can_deny_dangerous_drop_without_regex(self):
        path = self.policy_path("safety_policy_test_sql_dangerous_action.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "deny-dangerous-drop",
                        "name": "禁止数据库高危删除",
                        "domain": "database",
                        "platform": "Oracle",
                        "category": "sql",
                        "decision": "deny",
                        "matchers": [{"type": "sql_action", "value": "sql.dangerous_drop"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "db_execute_query",
                    {"sql": "DROP USER old_user CASCADE"},
                    {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "deny")
        self.assertIn("高危删除", result["reason"])

    def test_semantic_rule_sources_limit_trigger_source(self):
        path = self.policy_path("safety_policy_test_sources.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "alert-only",
                        "name": "告警联动禁止删除 Pod",
                        "domain": "cloudnative",
                        "platform": "Kubernetes",
                        "category": "http",
                        "decision": "deny",
                        "sources": ["alert"],
                        "matchers": [{"type": "platform_action", "value": "k8s.delete_pod"}],
                    }
                ]
                save_safety_policy(policy)
                args = {"method": "DELETE", "path": "/api/v1/namespaces/default/pods/nginx"}
                chat_result = explain_policy_decision(
                    "k8s_api_request",
                    args,
                    {"allow_modifications": True, "asset_type": "k8s", "trigger_source": "chat"},
                )
                alert_result = explain_policy_decision(
                    "k8s_api_request",
                    args,
                    {"allow_modifications": True, "asset_type": "k8s", "trigger_source": "alert"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertNotEqual(chat_result["decision"], "deny")
        self.assertEqual(alert_result["decision"], "deny")

    def test_semantic_platform_action_matches_middleware_publish_config(self):
        path = self.policy_path("safety_policy_test_middleware_action.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "nacos-publish",
                        "name": "Nacos 发布配置需要审批",
                        "domain": "middleware",
                        "platform": "Nacos",
                        "category": "http",
                        "decision": "approval",
                        "matchers": [{"type": "platform_action", "value": "nacos.publish_config"}],
                    }
                ]
                save_safety_policy(policy)
                result = explain_policy_decision(
                    "middleware_api_request",
                    {"method": "POST", "path": "/nacos/v1/cs/configs"},
                    {"allow_modifications": True, "asset_type": "nacos", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(result["decision"], "approval")
        self.assertIn("Nacos", result["reason"])

    def test_semantic_platform_action_matches_cicd_and_ai_actions(self):
        path = self.policy_path("safety_policy_test_cicd_ai_actions.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "prod-deploy",
                        "name": "生产发布需要审批",
                        "domain": "cicd",
                        "platform": "Jenkins",
                        "category": "http",
                        "decision": "approval",
                        "matchers": [{"type": "platform_action", "value": "cicd.deploy_prod"}],
                    },
                    {
                        "id": "delete-model",
                        "name": "禁止删除生产模型",
                        "domain": "ai",
                        "platform": "MLflow",
                        "category": "http",
                        "decision": "deny",
                        "matchers": [{"type": "platform_action", "value": "mlflow.delete_model_version"}],
                    },
                ]
                save_safety_policy(policy)
                deploy_result = explain_policy_decision(
                    "cicd_api_request",
                    {"method": "POST", "path": "/job/prod-deploy/build"},
                    {"allow_modifications": True, "asset_type": "jenkins", "protocol": "http_api"},
                )
                model_result = explain_policy_decision(
                    "ai_platform_api_request",
                    {"method": "DELETE", "path": "/models/prod/versions/12"},
                    {"allow_modifications": True, "asset_type": "mlflow", "protocol": "http_api"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertEqual(deploy_result["decision"], "approval")
        self.assertEqual(model_result["decision"], "deny")

    def test_semantic_rule_scope_supports_data_center_and_tenant(self):
        path = self.policy_path("safety_policy_test_datacenter_tenant_scope.json")
        self.cleanup_policy_file(path)
        try:
            with patch("core.safety_policy.POLICY_PATH", path):
                policy = get_safety_policy()
                policy["rules"] = [
                    {
                        "id": "az1-migrate-vm",
                        "name": "上海 AZ1 禁止迁移虚拟机",
                        "domain": "virtualization",
                        "platform": "VMware",
                        "category": "http",
                        "decision": "deny",
                        "scope": {"type": "data_center", "value": "上海-AZ1"},
                        "matchers": [{"type": "platform_action", "value": "virtualization.migrate_vm"}],
                    },
                    {
                        "id": "pay-release",
                        "name": "支付业务生产发布需要审批",
                        "domain": "cicd",
                        "platform": "Jenkins",
                        "category": "http",
                        "decision": "approval",
                        "scope": {"type": "tenant", "value": "支付"},
                        "matchers": [{"type": "platform_action", "value": "cicd.deploy_prod"}],
                    },
                ]
                save_safety_policy(policy)
                vm_args = {"method": "POST", "path": "/vms/prod-01/migrate"}
                other_dc = explain_policy_decision(
                    "virtualization_api_request",
                    vm_args,
                    {"allow_modifications": True, "asset_type": "vmware", "data_center": "北京-AZ1"},
                )
                shanghai_dc = explain_policy_decision(
                    "virtualization_api_request",
                    vm_args,
                    {"allow_modifications": True, "asset_type": "vmware", "data_center": "上海-AZ1"},
                )
                pay_release = explain_policy_decision(
                    "cicd_api_request",
                    {"method": "POST", "path": "/job/prod-deploy/build"},
                    {"allow_modifications": True, "asset_type": "jenkins", "tenant": "支付"},
                )
        finally:
            self.cleanup_policy_file(path)

        self.assertNotEqual(other_dc["decision"], "deny")
        self.assertEqual(shanghai_dc["decision"], "deny")
        self.assertEqual(pay_release["decision"], "approval")

    def test_invalid_regex_policy_is_rejected(self):
        policy = get_safety_policy()
        policy["rules"] = [
            {
                "id": "bad-regex",
                "name": "坏正则",
                "decision": "deny",
                "matchers": [{"type": "regex", "value": "["}],
            }
        ]

        issues = validate_safety_policy(policy)

        self.assertTrue(issues)
        self.assertIn("正则无效", issues[0])


if __name__ == "__main__":
    unittest.main()
