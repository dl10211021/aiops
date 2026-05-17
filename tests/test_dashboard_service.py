import unittest
from unittest.mock import patch

from core import dashboard_service


class FakeDashboardMemory:
    messages = []

    def get_all_assets(self):
        return [
            {
                "id": 1,
                "host": "10.0.0.10",
                "port": 22,
                "remark": "linux",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {"category": "os"},
            }
        ]

    def get_messages(self, session_id, for_ui=False, limit=None):
        messages = [item for item in self.messages if item.get("session_id") == session_id]
        return messages[-limit:] if limit else messages


class TestDashboardService(unittest.TestCase):
    def test_overview_payload_combines_assets_sessions_jobs_alerts_and_runs(self):
        with (
            patch.object(dashboard_service.CronManager, "get_all_jobs", return_value=[{"status": "scheduled"}]),
            patch.object(dashboard_service, "alert_summary", return_value={"open": 2}),
            patch.object(dashboard_service, "run_summary", return_value={"success_rate": 100.0}),
        ):
            payload = dashboard_service.build_dashboard_overview_payload(
                {
                    "sid-1": {
                        "info": {
                            "asset_type": "linux",
                            "protocol": "ssh",
                            "host": "10.0.0.10",
                            "port": 22,
                        }
                    }
                },
                memory_db=FakeDashboardMemory(),
            )

        self.assertEqual(payload["summary"]["asset_total"], 1)
        self.assertEqual(payload["summary"]["active_sessions"], 1)
        self.assertEqual(payload["alerts"]["open"], 2)
        self.assertEqual(payload["jobs"]["scheduled"], 1)
        self.assertEqual(payload["inspection_runs"]["success_rate"], 100.0)
        self.assertEqual(payload["run_trace_audit"]["session_count"], 1)

    def test_run_trace_audit_overview_aggregates_active_sessions(self):
        memory = FakeDashboardMemory()
        memory.messages = [
            {
                "id": 1,
                "session_id": "sid-1",
                "memory_type": "aiops_run_trace",
                "run_id": "run-1",
                "run_event_type": "run:start",
                "run_event_ts": 1.0,
                "run_event_payload": {
                    "run_id": "run-1",
                    "context": {
                        "context_sources": [
                            {"source": "knowledge_base", "enabled": True, "hit": True},
                            {"source": "asset_profile", "enabled": True, "hit": False, "status": "error"},
                        ],
                        "prompt_modules": {
                            "modules": ["evidence_contract", "rag_context"],
                            "enabled": {"evidence_contract": True, "rag_context": False},
                        },
                    },
                },
            },
            {
                "id": 2,
                "session_id": "sid-2",
                "memory_type": "aiops_run_trace",
                "run_id": "run-2",
                "run_event_type": "run:start",
                "run_event_ts": 2.0,
                "run_event_payload": {"run_id": "run-2"},
            },
            {
                "id": 3,
                "session_id": "sid-2",
                "memory_type": "aiops_run_trace",
                "run_id": "run-2",
                "run_event_type": "tool:after",
                "run_event_ts": 3.0,
                "run_event_payload": {
                    "run_id": "run-2",
                    "status": "error",
                    "result_meta": {
                        "runtime_execution": {
                            "attempts": 2,
                            "max_attempts": 2,
                            "retried": True,
                            "concurrent": True,
                            "final_status": "error",
                            "error_type": "tool_timeout",
                        }
                    },
                },
            },
        ]

        payload = dashboard_service.build_run_trace_audit_overview(
            {
                "sid-1": {"info": {"remark": "生产数据库", "host": "db.local", "protocol": "mysql", "tags": ["数据库"]}},
                "sid-2": {"info": {"remark": "旧会话", "protocol": "ssh"}},
            },
            memory_db=memory,
        )

        self.assertEqual(payload["session_count"], 2)
        self.assertEqual(payload["sessions_with_trace"], 2)
        self.assertEqual(payload["sessions_with_audit"], 1)
        self.assertEqual(payload["sessions_with_gaps"], 1)
        self.assertEqual(payload["run_count"], 2)
        self.assertEqual(payload["audited_run_count"], 1)
        self.assertEqual(payload["unaudited_run_count"], 1)
        self.assertEqual(payload["context_hits"], 1)
        self.assertEqual(payload["context_errors"], 1)
        self.assertEqual(payload["prompt_modules"], 2)
        self.assertEqual(payload["runtime_tool_count"], 1)
        self.assertEqual(payload["runtime_error_count"], 1)
        self.assertEqual(payload["runtime_timeout_count"], 1)
        self.assertEqual(payload["runtime_retry_count"], 1)
        self.assertEqual(payload["runtime_concurrent_count"], 1)
        self.assertEqual(payload["runtime_error_types"]["tool_timeout"], 1)
        self.assertEqual(payload["source_counts"]["knowledge_base"]["hit"], 1)
        self.assertEqual(payload["module_counts"]["rag_context"]["disabled"], 1)
        self.assertEqual(payload["sessions"][0]["session_id"], "sid-2")
        self.assertEqual(payload["sessions"][0]["runtime_timeout_count"], 1)

    def test_run_trace_audit_markdown_report_summarizes_runtime_and_gaps(self):
        overview = {
            "session_count": 2,
            "sessions_with_trace": 2,
            "run_count": 3,
            "audited_run_count": 2,
            "unaudited_run_count": 1,
            "context_hits": 4,
            "context_sources": 5,
            "context_errors": 1,
            "prompt_modules": 3,
            "runtime_tool_count": 8,
            "runtime_error_count": 2,
            "runtime_timeout_count": 1,
            "runtime_retry_count": 2,
            "runtime_concurrent_count": 4,
            "runtime_untracked_count": 1,
            "runtime_error_types": {"tool_timeout": 1, "tool_execution_failed": 1},
            "sessions": [
                {
                    "session_id": "sid-2",
                    "label": "旧会话",
                    "protocol": "ssh",
                    "run_count": 1,
                    "unaudited_run_count": 1,
                    "context_errors": 0,
                    "runtime_timeout_count": 1,
                    "runtime_retry_count": 1,
                }
            ],
        }

        markdown = dashboard_service.format_run_trace_audit_markdown(overview)

        self.assertIn("# OpsCore Run Trace 审计报表", markdown)
        self.assertIn("- 审计覆盖: 2/3", markdown)
        self.assertIn("- 未审计运行: 1", markdown)
        self.assertIn("- 实际超时: 1", markdown)
        self.assertIn("| 旧会话 | ssh | 1 | 1 | 1 | 1 |", markdown)
        self.assertIn("tool_timeout: 1", markdown)

    def test_alert_trend_and_risk_ranking_payloads_use_alert_store(self):
        alerts = [
            {"created_at": "2026-05-01 10:00:00", "severity": "critical", "host": "db-1"},
            {"created_at": "2026-05-01 11:00:00", "severity": "warning", "host": "db-1"},
            {"created_at": "2026-05-01 12:00:00", "severity": "info", "host": "web-1"},
        ]
        with patch.object(dashboard_service, "list_alert_events", return_value=alerts):
            trend = dashboard_service.build_dashboard_alert_trend_payload()
            ranking = dashboard_service.build_dashboard_risk_ranking_payload()

        self.assertEqual(trend["points"][0]["total"], 3)
        self.assertEqual(ranking["ranking"][0]["host"], "db-1")

    def test_inspection_run_trend_payload_wraps_points(self):
        with patch.object(dashboard_service, "run_trend", return_value=[{"date": "2026-05-01", "total": 1}]):
            payload = dashboard_service.build_dashboard_inspection_run_trend_payload()

        self.assertEqual(payload["points"][0]["total"], 1)
