import unittest

from core import safety_policy
from core.safety_action_decisions import (
    action_reason,
    collect_action_rule_decisions,
    top_action_decision,
)


class SafetyActionDecisionTests(unittest.TestCase):
    def test_collect_action_rule_decisions_filters_invalid_and_unknown_rules(self):
        policy = {
            "action_rules": {
                "sql": {
                    "sql.read": "allow",
                    "sql.drop": "deny",
                    "sql.update": "review",
                }
            }
        }

        self.assertEqual(
            collect_action_rule_decisions(
                policy,
                category="sql",
                actions=["sql.update", "sql.drop", "sql.read", "sql.unknown"],
            ),
            [("sql.read", "allow"), ("sql.drop", "deny")],
        )

    def test_top_action_decision_prefers_deny_then_approval_then_allow(self):
        policy = {
            "action_rules": {
                "sql": {
                    "sql.read": "allow",
                    "sql.drop": "deny",
                    "sql.update": "approval",
                }
            }
        }

        action, decision, reason = top_action_decision(
            policy,
            category="sql",
            actions=["sql.read", "sql.update", "sql.drop"],
        )

        self.assertEqual((action, decision), ("sql.drop", "deny"))
        self.assertIn("禁止执行", reason)

    def test_action_reason_preserves_instance_admin_label_override(self):
        self.assertEqual(
            action_reason("sql.instance_admin", "approval"),
            "数据库实例级管理 已被动作策略设置为需要人工审批。",
        )

    def test_safety_policy_wrappers_preserve_existing_entrypoints(self):
        policy = {
            "action_rules": {
                "sql": {
                    "sql.read": "allow",
                    "sql.schema_change": "deny",
                }
            }
        }

        self.assertEqual(
            safety_policy._action_rule_decisions(
                policy,
                "db_execute_query",
                {"sql": "DROP TABLE users"},
            ),
            [("sql.schema_change", "deny")],
        )
        self.assertEqual(safety_policy._action_reason("sql.read", "allow"), action_reason("sql.read", "allow"))


if __name__ == "__main__":
    unittest.main()
