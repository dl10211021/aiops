import unittest

from core import safety_policy
from core.safety_policy_config import (
    DEFAULT_SAFETY_POLICY,
    normalize_safety_policy,
    validate_safety_policy,
)


class SafetyPolicyConfigTests(unittest.TestCase):
    def test_normalize_policy_clamps_timeout_and_cleans_rules(self):
        policy = normalize_safety_policy(
            {
                "approval_timeout_seconds": "5",
                "rules": [
                    {
                        "id": "r1",
                        "name": "SQL 只读放行",
                        "decision": "ALLOW",
                        "matchers": [{"type": "contains", "value": "select"}],
                        "sources": [" api ", ""],
                    },
                    {"decision": "invalid", "matchers": [{"type": "contains", "value": "drop"}]},
                ],
            }
        )

        self.assertEqual(policy["approval_timeout_seconds"], 30)
        self.assertEqual(len(policy["rules"]), 1)
        self.assertEqual(policy["rules"][0]["decision"], "allow")
        self.assertEqual(policy["rules"][0]["sources"], ["api"])

    def test_validate_policy_reports_regex_and_cidr_errors(self):
        policy = normalize_safety_policy(
            {
                "categories": {"linux": {"approval_patterns": ["["]}},
                "network_boundary": {"active_cidrs": ["not-a-cidr"]},
            }
        )

        issues = validate_safety_policy(policy)

        self.assertTrue(any("linux.approval_patterns" in issue for issue in issues))
        self.assertTrue(any("network_boundary.active_cidrs" in issue for issue in issues))

    def test_safety_policy_keeps_backward_compatible_config_exports(self):
        self.assertIs(safety_policy.DEFAULT_SAFETY_POLICY, DEFAULT_SAFETY_POLICY)
        self.assertIs(safety_policy.normalize_safety_policy, normalize_safety_policy)
        self.assertIs(safety_policy.validate_safety_policy, validate_safety_policy)


if __name__ == "__main__":
    unittest.main()
