import unittest

from core.tool_policy_validation import validate_tool_runtime_policy


class ToolPolicyValidationTests(unittest.TestCase):
    def test_rejects_controlled_tool_without_approval(self):
        issues = validate_tool_runtime_policy(
            "unsafe_write",
            {
                "operation_mode": "read_write",
                "approval_policy": "none",
                "concurrency_safe": True,
                "timeout_policy": {"default_seconds": 60},
                "retry_policy": {"max_attempts": 2},
            },
        )

        self.assertIn("unsafe_write:read_write:none:controlled_tool_without_approval", issues)
        self.assertIn("unsafe_write:read_write:none:controlled_tool_marked_concurrency_safe", issues)
        self.assertIn("unsafe_write:read_write:none:controlled_tool_retries_enabled", issues)

    def test_rejects_destructive_tool_without_strict_flags(self):
        issues = validate_tool_runtime_policy(
            "delete_everything",
            {
                "operation_mode": "destructive",
                "approval_policy": "guarded_write",
                "destructive": False,
                "timeout_policy": {"default_seconds": 60},
                "retry_policy": {"max_attempts": 1},
            },
        )

        self.assertIn("delete_everything:destructive:guarded_write:destructive_flag_missing", issues)
        self.assertIn(
            "delete_everything:destructive:guarded_write:destructive_tool_not_always_required",
            issues,
        )

    def test_rejects_external_effect_without_audit_only_storage(self):
        issues = validate_tool_runtime_policy(
            "send_message",
            {
                "operation_mode": "external_effect",
                "approval_policy": "guarded_write",
                "result_store_policy": "evidence",
                "timeout_policy": {"default_seconds": 45},
                "retry_policy": {"max_attempts": 1},
            },
        )

        self.assertEqual(
            issues,
            ["send_message:external_effect:guarded_write:external_effect_not_audit_only"],
        )

    def test_accepts_read_policy_with_timeout_and_retry_bounds(self):
        issues = validate_tool_runtime_policy(
            "read_status",
            {
                "operation_mode": "read",
                "approval_policy": "none",
                "timeout_policy": {"default_seconds": 45},
                "retry_policy": {"max_attempts": 2, "retry_on": ["timeout", "connection_error"]},
            },
        )

        self.assertEqual(issues, [])

    def test_rejects_unknown_retry_reason(self):
        issues = validate_tool_runtime_policy(
            "read_status",
            {
                "operation_mode": "read",
                "approval_policy": "none",
                "timeout_policy": {"default_seconds": 45},
                "retry_policy": {"max_attempts": 2, "retry_on": ["timeout", "network_glitch"]},
            },
        )

        self.assertEqual(
            issues,
            ["read_status:read:none:invalid_retry_reason:network_glitch"],
        )

    def test_rejects_non_list_retry_on(self):
        issues = validate_tool_runtime_policy(
            "read_status",
            {
                "operation_mode": "read",
                "approval_policy": "none",
                "timeout_policy": {"default_seconds": 45},
                "retry_policy": {"max_attempts": 2, "retry_on": "timeout"},
            },
        )

        self.assertEqual(issues, ["read_status:read:none:invalid_retry_on"])

    def test_rejects_non_numeric_retry_delay(self):
        issues = validate_tool_runtime_policy(
            "read_status",
            {
                "operation_mode": "read",
                "approval_policy": "none",
                "timeout_policy": {"default_seconds": 45},
                "retry_policy": {"max_attempts": 2, "delay_seconds": "soon"},
            },
        )

        self.assertEqual(issues, ["read_status:read:none:invalid_retry_delay"])


if __name__ == "__main__":
    unittest.main()
