import os
import unittest
from pathlib import Path
from unittest.mock import patch

from core.safety_policy import (
    check_approval_needed,
    check_readonly_block,
    get_safety_policy,
    save_safety_policy,
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


if __name__ == "__main__":
    unittest.main()
