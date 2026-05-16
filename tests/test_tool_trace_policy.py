import unittest

from core.tool_trace_policy import (
    policy_summary,
    trace_evidence_id,
    trace_policy_summary,
    trace_runtime_summary,
    trace_sql_action_summary,
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

    def test_trace_runtime_summary_reports_timeout_and_retry(self):
        trace = {
            "resultMeta": {
                "runtime_policy": {
                    "attempts": 2,
                    "max_attempts": 2,
                    "retried": True,
                    "final_status": "error",
                    "error_type": "tool_timeout",
                    "timeout_seconds": 30,
                }
            }
        }

        self.assertEqual(trace_runtime_summary(trace), "timeout:30s,retry:2/2")

    def test_trace_runtime_summary_falls_back_to_evidence_metadata(self):
        trace = {
            "evidence": {
                "result_meta": {
                    "runtime_execution": {
                        "attempts": 2,
                        "max_attempts": 3,
                        "retried": True,
                        "final_status": "success",
                    }
                }
            }
        }

        self.assertEqual(trace_runtime_summary(trace), "retry:2/3")

    def test_trace_sql_action_summary_prefers_result_metadata(self):
        trace = {
            "tool": "db_execute_query",
            "resultMeta": {"statement_type": "select"},
            "args": "delete from audit_log",
        }

        self.assertEqual(trace_sql_action_summary(trace), "只读查询 (SELECT)")

    def test_trace_sql_action_summary_reads_evidence_metadata(self):
        trace = {
            "tool": "db_execute_query",
            "evidence": {"result_meta": {"statement_type": "alter"}},
            "args": "select * from v$database",
        }

        self.assertEqual(trace_sql_action_summary(trace), "写入/DDL (ALTER)")

    def test_trace_sql_action_summary_falls_back_to_sql_args(self):
        trace = {
            "tool": "db_execute_query",
            "args": "\n  explain plan for select * from dba_tables",
        }

        self.assertEqual(trace_sql_action_summary(trace), "只读查询 (EXPLAIN)")


if __name__ == "__main__":
    unittest.main()
