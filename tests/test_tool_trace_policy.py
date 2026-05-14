import unittest

from core.tool_trace_policy import (
    policy_summary,
    trace_evidence_id,
    trace_policy_summary,
    trace_tool_policy,
)


class ToolTracePolicyTests(unittest.TestCase):
    def test_extracts_evidence_id_from_camel_case_or_evidence_payload(self):
        self.assertEqual(trace_evidence_id({"evidenceId": "tev-1"}), "tev-1")
        self.assertEqual(
            trace_evidence_id({"evidence": {"evidence_id": "tev-2"}}),
            "tev-2",
        )

    def test_prefers_result_meta_policy_before_evidence_policy(self):
        trace = {
            "tool": "db_execute_query",
            "resultMeta": {
                "tool_policy": {
                    "operation_mode": "read",
                    "approval_policy": "none",
                    "evidence_family": "database",
                }
            },
            "evidence": {
                "result_meta": {
                    "tool_policy": {
                        "operation_mode": "write",
                        "approval_policy": "always_required",
                        "evidence_family": "host_cli",
                    }
                }
            },
        }

        self.assertEqual(
            trace_tool_policy(trace),
            {
                "operation_mode": "read",
                "approval_policy": "none",
                "evidence_family": "database",
            },
        )
        self.assertEqual(trace_policy_summary(trace), "read/none/database")

    def test_can_fallback_to_registry_or_skip_fallback(self):
        trace = {"tool": "db_execute_query"}

        self.assertEqual(
            trace_policy_summary(trace),
            "read_write/guarded_write/database",
        )
        self.assertEqual(
            trace_tool_policy(trace, fallback_to_registry=False),
            {},
        )
        self.assertEqual(policy_summary({}), "")


if __name__ == "__main__":
    unittest.main()
