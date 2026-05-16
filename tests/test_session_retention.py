import datetime as dt
import asyncio
import json
import sqlite3
import unittest

from core.session_retention import (
    SessionRetentionPolicy,
    apply_session_retention,
    latest_session_retention_status,
    session_retention_maintenance_loop,
    summarize_tool_result,
)


def setup_memory(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            message_json TEXT,
            is_compressed INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def insert_message(
    conn: sqlite3.Connection,
    *,
    session_id: str = "sid-1",
    message: dict,
    timestamp: str,
    is_compressed: int = 0,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO memory (session_id, message_json, is_compressed, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, json.dumps(message, ensure_ascii=False), is_compressed, timestamp),
    )
    return int(cur.lastrowid)


class TestSessionRetention(unittest.TestCase):
    def make_memory_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        setup_memory(conn)
        return conn

    def test_summarize_tool_result_keeps_operational_metadata(self):
        summary = summarize_tool_result(
            json.dumps(
                {
                    "success": True,
                    "statement_type": "select",
                    "count": 31,
                    "tool_policy": {
                        "operation_mode": "read_write",
                        "approval_policy": "guarded_write",
                        "evidence_family": "database",
                    },
                    "data": [{"TABLESPACE_NAME": "USERS", "PCT_USED": 93.2}],
                },
                ensure_ascii=False,
            )
        )

        self.assertIn('"success": true', summary)
        self.assertIn('"statement_type": "select"', summary)
        self.assertIn('"count": 31', summary)
        self.assertIn('"tool_policy"', summary)
        self.assertIn('"evidence_family": "database"', summary)
        self.assertIn("TABLESPACE_NAME", summary)

    def test_apply_session_retention_compacts_old_tool_rows_and_trace_results(self):
        conn = self.make_memory_conn()
        insert_message(
            conn,
            message={
                "role": "assistant",
                "content": "已查询",
                "exec_trace": [
                    {
                        "tool": "db_execute_query",
                        "args": "select * from dba_data_files",
                        "result": json.dumps({"success": True, "data": [{"FILE_ID": 1}]}),
                        "status": "done",
                    }
                ],
            },
            timestamp="2026-03-01 00:00:00",
        )
        insert_message(
            conn,
            message={
                "role": "tool",
                "tool_call_id": "call-1",
                "name": "db_execute_query",
                "content": json.dumps({"success": True, "count": 1, "data": [{"FILE_ID": 1}]}),
            },
            timestamp="2026-03-01 00:00:00",
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, compressed_history_days=180),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )

        self.assertEqual(stats["rows_scanned"], 2)
        self.assertEqual(stats["rows_compacted"], 2)
        messages = [
            json.loads(row[0])
            for row in conn.execute("SELECT message_json FROM memory ORDER BY id ASC").fetchall()
        ]
        trace = messages[0]["exec_trace"][0]
        self.assertEqual(trace["args"], "select * from dba_data_files")
        self.assertEqual(trace["result_retention"], "summary_after_30_days")
        self.assertIn("result_summary", trace["result"])
        self.assertTrue(messages[1]["retention_compacted"])
        self.assertIn("result_summary", messages[1]["content"])

    def test_apply_session_retention_scans_only_cutoff_candidates(self):
        conn = self.make_memory_conn()
        insert_message(
            conn,
            message={"role": "tool", "content": json.dumps({"success": True, "output": "old"})},
            timestamp="2026-03-01 00:00:00",
        )
        insert_message(
            conn,
            message={"role": "tool", "content": json.dumps({"success": True, "output": "recent"})},
            timestamp="2026-05-09 00:00:00",
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, compressed_history_days=180),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )

        self.assertEqual(stats["rows_scanned"], 1)
        self.assertEqual(stats["rows_compacted"], 1)
        messages = [
            json.loads(row[0])
            for row in conn.execute("SELECT message_json FROM memory ORDER BY id ASC").fetchall()
        ]
        self.assertTrue(messages[0]["retention_compacted"])
        self.assertNotIn("retention_compacted", messages[1])

    def test_apply_session_retention_deletes_only_compressed_old_rows_with_audit(self):
        conn = self.make_memory_conn()
        old_compressed_id = insert_message(
            conn,
            message={
                "role": "assistant",
                "content": "旧内容",
                "exec_trace": [
                    {
                        "tool": "db_execute_query",
                        "args": "alter system checkpoint",
                        "evidenceId": "tev-sid-1-call-1",
                        "resultMeta": {
                            "statement_type": "alter",
                            "tool_policy": {
                                "operation_mode": "read_write",
                                "approval_policy": "guarded_write",
                                "evidence_family": "database",
                            }
                        },
                    }
                ],
            },
            timestamp="2025-01-01 00:00:00",
            is_compressed=1,
        )
        old_uncompressed_id = insert_message(
            conn,
            message={"role": "assistant", "content": "未压缩内容"},
            timestamp="2025-01-01 00:00:00",
            is_compressed=0,
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, compressed_history_days=180),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )

        self.assertEqual(stats["rows_deleted"], 1)
        remaining_ids = [
            row[0] for row in conn.execute("SELECT id FROM memory ORDER BY id ASC").fetchall()
        ]
        self.assertEqual(remaining_ids, [old_uncompressed_id])
        audit = conn.execute(
            "SELECT message_id, action, summary FROM session_retention_audit"
        ).fetchone()
        self.assertEqual(audit[0], old_compressed_id)
        self.assertEqual(audit[1], "delete_compressed_history")
        self.assertIn("db_execute_query", audit[2])
        self.assertIn("tev-sid-1-call-1", audit[2])
        self.assertIn("read_write/guarded_write/database", audit[2])
        self.assertIn("sql_action=写入/DDL (ALTER)", audit[2])

    def test_dry_run_reports_without_mutating(self):
        conn = self.make_memory_conn()
        insert_message(
            conn,
            message={"role": "tool", "content": json.dumps({"success": True, "output": "x"})},
            timestamp="2026-03-01 00:00:00",
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
            dry_run=True,
        )

        self.assertEqual(stats["rows_compacted"], 1)
        message = json.loads(conn.execute("SELECT message_json FROM memory").fetchone()[0])
        self.assertNotIn("retention_compacted", message)

    def test_apply_session_retention_expires_old_audit_metadata(self):
        conn = self.make_memory_conn()
        apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, audit_metadata_days=365),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )
        conn.execute(
            """
            INSERT INTO session_retention_audit (
                session_id, message_id, role, original_timestamp, action, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("sid-1", 1, "assistant", "2024-01-01 00:00:00", "delete", "old", "2024-01-01 00:00:00"),
        )
        conn.execute(
            """
            INSERT INTO session_retention_audit (
                session_id, message_id, role, original_timestamp, action, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("sid-1", 2, "assistant", "2026-04-01 00:00:00", "delete", "new", "2026-04-01 00:00:00"),
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, audit_metadata_days=365),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )

        self.assertEqual(stats["audit_rows_deleted"], 1)
        remaining = conn.execute(
            "SELECT message_id FROM session_retention_audit ORDER BY id"
        ).fetchall()
        self.assertEqual(remaining, [(2,)])

    def test_apply_session_retention_creates_indexes_and_records_last_run(self):
        conn = self.make_memory_conn()
        insert_message(
            conn,
            message={"role": "tool", "content": json.dumps({"success": True, "output": "old"})},
            timestamp="2026-03-01 00:00:00",
        )

        stats = apply_session_retention(
            conn,
            policy=SessionRetentionPolicy(raw_result_days=30, compressed_history_days=180),
            now=dt.datetime(2026, 5, 10, 0, 0, 0),
        )
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' ORDER BY name"
            ).fetchall()
        }
        status = latest_session_retention_status(conn, interval_seconds=3600)

        self.assertIn("idx_memory_retention_timestamp_compressed", indexes)
        self.assertIn("idx_session_retention_audit_created_at", indexes)
        self.assertIn("idx_session_retention_runs_completed_at", indexes)
        self.assertEqual(stats["rows_scanned"], 1)
        self.assertEqual(status["interval_seconds"], 3600)
        self.assertEqual(status["last_run"]["rows_scanned"], 1)
        self.assertEqual(status["last_run"]["rows_compacted"], 1)
        self.assertEqual(status["last_run"]["status"], "completed")
        self.assertIsNotNone(status["next_run_at"])

    def test_session_retention_maintenance_loop_runs_on_interval(self):
        calls = []
        sleeps = []

        async def runner():
            calls.append("run")
            return {
                "rows_scanned": len(calls),
                "rows_compacted": 0,
                "rows_deleted": 0,
                "audit_rows_deleted": 0,
            }

        async def sleep(seconds):
            sleeps.append(seconds)

        asyncio.run(
            session_retention_maintenance_loop(
                interval_seconds=12,
                runner=runner,
                sleep=sleep,
                max_runs=2,
            )
        )

        self.assertEqual(calls, ["run", "run"])
        self.assertEqual(sleeps, [12])


if __name__ == "__main__":
    unittest.main()
