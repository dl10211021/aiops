import os
import unittest
from pathlib import Path
from unittest.mock import patch

from core.safety_policy import (
    check_approval_needed,
    check_readonly_block,
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
