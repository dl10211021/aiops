import unittest

from core.session_export import chat_history_messages, format_session_history_markdown


class TestSessionExport(unittest.TestCase):
    def test_format_session_history_markdown_includes_attachment_details(self):
        markdown = format_session_history_markdown(
            [
                {"role": "system", "content": "ignore"},
                {
                    "role": "user",
                    "content": "请分析附件",
                    "attachments": [
                        {
                            "filename": "assets.xlsx",
                            "ext": ".xlsx",
                            "size": 1200,
                            "rows": 3,
                            "pages": None,
                            "truncated": True,
                        }
                    ],
                },
                {"role": "assistant", "content": "分析完成"},
            ],
            "oracle-01",
        )

        self.assertIn("# Chat History: oracle-01", markdown)
        self.assertIn("## User", markdown)
        self.assertIn("### Attachments", markdown)
        self.assertIn("- assets.xlsx (.xlsx；1200 bytes；3 行；已截断)", markdown)
        self.assertIn("## AI Assistant", markdown)

    def test_chat_history_messages_filters_non_chat_roles(self):
        messages = chat_history_messages(
            [
                {"role": "system", "content": "ignore"},
                {"role": "user", "content": "keep"},
                {"role": "tool", "content": "ignore"},
                {"role": "assistant", "content": "keep"},
            ]
        )

        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])

    def test_format_session_history_markdown_localizes_exec_trace_tool_names(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "巡检完成",
                    "exec_trace": [
                        {
                            "tool": "local_execute_script",
                            "status": "success",
                            "args": "uptime",
                            "result": "load average: 0.01",
                            "resultMeta": {
                                "tool_policy": {
                                    "operation_mode": "read_write",
                                    "approval_policy": "guarded_write",
                                    "evidence_family": "local_runtime",
                                }
                            },
                            "evidenceId": "tev-linux-01-call-1",
                        }
                    ],
                }
            ],
            "linux-01",
        )

        self.assertIn(
            "- Step 1: 本地技能脚本 (`local_execute_script`) [success]",
            markdown,
        )
        self.assertIn("  - Policy: 读写受控；写入受控；本地运行时", markdown)
        self.assertIn("  - Evidence: tev-linux-01-call-1", markdown)
        self.assertIn("  - Execute: uptime", markdown)
        self.assertIn("  - Result: load average: 0.01", markdown)

    def test_format_session_history_markdown_falls_back_to_tool_policy_metadata(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "查询完成",
                    "exec_trace": [
                        {
                            "tool": "db_execute_query",
                            "status": "done",
                            "args": "select 1 from dual",
                            "result": '{"success": true}',
                            "evidence": {
                                "evidence_id": "tev-db-1-call-1",
                                "result_meta": {},
                            },
                        }
                    ],
                }
            ],
            "oracle-01",
        )

        self.assertIn("  - Policy: 读写受控；写入受控；数据库证据", markdown)
        self.assertIn("  - SQL Action: 只读查询 (SELECT)", markdown)
        self.assertIn("  - Evidence: tev-db-1-call-1", markdown)

    def test_format_session_history_markdown_includes_runtime_retry_metadata(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "执行完成",
                    "exec_trace": [
                        {
                            "tool": "monitoring_api_query",
                            "status": "error",
                            "args": "GET /api/status",
                            "result": "timeout",
                            "resultMeta": {
                                "runtime_policy": {
                                    "attempts": 2,
                                    "max_attempts": 2,
                                    "retried": True,
                                }
                            },
                        }
                    ],
                }
            ],
            "elk-01",
        )

        self.assertIn("  - Runtime: 实际重试 2/2 次", markdown)

    def test_format_session_history_markdown_includes_runtime_timeout_metadata(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "执行失败",
                    "exec_trace": [
                        {
                            "tool": "monitoring_api_query",
                            "status": "error",
                            "args": "GET /api/status",
                            "result": "timeout",
                            "resultMeta": {
                                "runtime_policy": {
                                    "attempts": 1,
                                    "max_attempts": 1,
                                    "retried": False,
                                    "final_status": "error",
                                    "error_type": "tool_timeout",
                                    "timeout_seconds": 30,
                                }
                            },
                        }
                    ],
                }
            ],
            "elk-01",
        )

        self.assertIn("  - Runtime: 实际超时 30s", markdown)

    def test_format_session_history_markdown_includes_runtime_failure_metadata(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "执行失败",
                    "exec_trace": [
                        {
                            "tool": "monitoring_api_query",
                            "status": "error",
                            "args": "GET /api/status",
                            "result": "connection failed",
                            "resultMeta": {
                                "runtime_policy": {
                                    "attempts": 2,
                                    "max_attempts": 2,
                                    "retried": True,
                                    "final_status": "error",
                                    "error_type": "tool_connection_error",
                                }
                            },
                        }
                    ],
                }
            ],
            "elk-01",
        )

        self.assertIn("  - Runtime: 实际执行失败；实际重试 2/2 次", markdown)

    def test_format_session_history_markdown_reads_runtime_from_evidence_metadata(self):
        markdown = format_session_history_markdown(
            [
                {
                    "role": "assistant",
                    "content": "执行完成",
                    "exec_trace": [
                        {
                            "tool": "monitoring_api_query",
                            "status": "done",
                            "args": "GET /api/status",
                            "result": "ok",
                            "evidence": {
                                "result_meta": {
                                    "runtime_execution": {
                                        "attempts": 2,
                                        "max_attempts": 3,
                                        "retried": True,
                                        "final_status": "success",
                                    }
                                }
                            },
                        }
                    ],
                }
            ],
            "elk-01",
        )

        self.assertIn("  - Runtime: 实际重试 2/3 次", markdown)
