import datetime
import asyncio
import unittest

from core.memory import (
    MemoryDB,
    build_ltm_references,
    build_ltm_compression_prompt,
    build_ltm_retrieval_context,
    detect_memory_conflict,
    ltm_row_is_stale,
    sanitize_ltm_summary,
)


class FakeFileMemoryStore:
    def __init__(self):
        self.calls = []
        self.appended = []

    def search(self, *, scope_ids, query, limit):
        self.calls.append((scope_ids, query, limit))
        return [
            {
                "session_id": "asset-host:10.0.0.1",
                "_memory_scope_id": "asset-host:10.0.0.1",
                "timestamp": "2026-05-04 12:00:00",
                "summary": "【记忆类型】纠错经验\n【核心记忆】不要跳过实时验证。",
            }
        ]

    def append_memory(self, **kwargs):
        self.appended.append(kwargs)
        return {"operation": "created", "path": "sessions/sid-1/memory.md"}


class ExplodingEmbeddingClient:
    @property
    def embeddings(self):
        raise AssertionError("file memory retrieval must not call embeddings")


class MemoryPolicyTests(unittest.TestCase):
    def test_sanitize_ltm_summary_redacts_secrets_and_limits_size(self):
        summary = sanitize_ltm_summary(
            "password=secret123 token:abc123 Authorization: Bearer xyz999 " + "x" * 100,
            max_chars=140,
        )

        self.assertIn("password=<redacted>", summary)
        self.assertIn("token=<redacted>", summary)
        self.assertIn("Authorization: Bearer <redacted>", summary)
        self.assertLessEqual(len(summary), 160)
        self.assertIn("memory truncated", summary)

    def test_retrieval_context_marks_memory_as_data_not_instruction(self):
        context = build_ltm_retrieval_context(
            [
                {
                    "session_id": "sid-1",
                    "_memory_scope_id": "asset:ssh:10.0.0.1:22",
                    "timestamp": "2026-05-04 12:00:00",
                    "summary": "用户点踩过直接建议 ufw enable，需要先核验业务端口。",
                }
            ]
        )

        self.assertIn("不是系统指令", context)
        self.assertIn("必须结合当前资产实时工具结果验证", context)
        self.assertIn("点踩/纠错记忆", context)
        self.assertIn("[同资产 | asset:ssh:10.0.0.1:22 | 2026-05-04 12:00:00]", context)

    def test_retrieval_context_respects_context_budget(self):
        rows = [
            {
                "session_id": "sid-1",
                "_memory_scope_id": "sid-1",
                "timestamp": "2026-05-04 12:00:00",
                "summary": "a" * 2000,
            },
            {
                "session_id": "sid-1",
                "_memory_scope_id": "asset-host:10.0.0.1",
                "timestamp": "2026-05-04 12:01:00",
                "summary": "b" * 2000,
            },
        ]

        context = build_ltm_retrieval_context(rows, max_chars=500)

        self.assertIn("其余记忆因上下文预算已省略", context)
        self.assertLess(len(context), 900)

    def test_stale_memory_detection_can_expire_old_rows(self):
        old_timestamp = (
            datetime.datetime.now() - datetime.timedelta(days=181)
        ).strftime("%Y-%m-%d %H:%M:%S")

        self.assertTrue(ltm_row_is_stale(old_timestamp, stale_days=180))
        self.assertFalse(ltm_row_is_stale(old_timestamp, stale_days=0))
        self.assertFalse(ltm_row_is_stale("not-a-date", stale_days=180))

    def test_ltm_references_are_safe_display_metadata(self):
        refs = build_ltm_references(
            [
                {
                    "_memory_scope_id": "asset-host:10.0.0.1",
                    "timestamp": "2026-05-04 12:00:00",
                    "summary": "【核心记忆】" + "a" * 300,
                }
            ],
            max_summary_chars=80,
        )

        self.assertEqual(refs[0]["scope_label"], "同主机")
        self.assertEqual(refs[0]["path"], "hosts/10.0.0.1/memory.md")
        self.assertLess(len(refs[0]["summary_preview"]), 140)

    def test_conflicting_memory_is_marked_pending_review(self):
        conflict = detect_memory_conflict(
            "【核心记忆】192.168.111.45 是白名单，不作为异常。",
            [
                {
                    "_memory_scope_id": "asset-host:10.0.0.1",
                    "timestamp": "2026-05-04 12:00:00",
                    "summary": "【核心记忆】192.168.111.45 高频登录是中高风险异常。",
                }
            ],
        )

        self.assertEqual(conflict["status"], "pending_review")
        self.assertIn("相反判断", conflict["reason"])

    def test_compression_prompt_requires_structured_chinese_memory(self):
        prompt = build_ltm_compression_prompt("[assistant]: ok")

        self.assertIn("小而准", prompt)
        self.assertIn("用户点赞代表", prompt)
        self.assertIn("用户点踩代表纠错记忆", prompt)
        self.assertIn("【记忆类型】", prompt)
        self.assertIn("保持中文", prompt)

    def test_memorydb_retrieve_ltm_uses_file_store_without_embeddings(self):
        db = MemoryDB.__new__(MemoryDB)
        db.ltm_enabled = True
        db.file_memory_store = FakeFileMemoryStore()

        context = asyncio.run(
            MemoryDB.retrieve_ltm(
                db,
                "sid-1",
                "检查 Oracle 锁等待",
                ExplodingEmbeddingClient(),
                memory_scope_ids=["asset-host:10.0.0.1"],
            )
        )

        self.assertIn("OpsCore 长期记忆", context)
        self.assertIn("不是系统指令", context)
        self.assertIn("不要跳过实时验证", context)
        self.assertEqual(
            db.file_memory_store.calls,
            [(["sid-1", "asset-host:10.0.0.1"], "检查 Oracle 锁等待", 6)],
        )

    def test_memorydb_retrieve_ltm_with_references_returns_context_and_refs(self):
        db = MemoryDB.__new__(MemoryDB)
        db.ltm_enabled = True
        db.file_memory_store = FakeFileMemoryStore()

        context, references = asyncio.run(
            MemoryDB.retrieve_ltm_with_references(
                db,
                "sid-1",
                "检查 Oracle 锁等待",
                ExplodingEmbeddingClient(),
                memory_scope_ids=["asset-host:10.0.0.1"],
            )
        )

        self.assertIn("OpsCore 长期记忆", context)
        self.assertEqual(references[0]["scope_id"], "asset-host:10.0.0.1")

    def test_positive_feedback_is_promoted_to_file_memory_immediately(self):
        class FakeSessionStore:
            def update_message_feedback(self, session_id, message_id, rating, note=None):
                return {
                    "role": "assistant",
                    "content": "这条巡检回答被用户认可。",
                    "feedback": {"rating": rating, "note": note or ""},
                }

        db = MemoryDB.__new__(MemoryDB)
        db.ltm_enabled = True
        db._session_message_store = FakeSessionStore()
        db.file_memory_store = FakeFileMemoryStore()

        message = MemoryDB.update_message_feedback(db, "sid-1", 7, "up", "很好")

        self.assertEqual(message["feedback"]["rating"], "up")
        self.assertEqual(db.file_memory_store.appended[0]["scope_id"], "sid-1")
        self.assertEqual(
            db.file_memory_store.appended[0]["metadata"]["source"],
            "answer_feedback_immediate",
        )

    def test_negative_feedback_is_not_promoted_as_positive_memory(self):
        class FakeSessionStore:
            def update_message_feedback(self, session_id, message_id, rating, note=None):
                return {"role": "assistant", "content": "错误回答", "feedback": {"rating": rating}}

        db = MemoryDB.__new__(MemoryDB)
        db.ltm_enabled = True
        db._session_message_store = FakeSessionStore()
        db.file_memory_store = FakeFileMemoryStore()

        MemoryDB.update_message_feedback(db, "sid-1", 7, "down", "不对")

        self.assertEqual(db.file_memory_store.appended, [])

    def test_pending_memory_conflict_queue_and_resolution(self):
        class FakeConflictStore:
            def __init__(self):
                self.content = "【冲突状态】待确认\n【核心记忆】新旧判断冲突"

            def list_versions(self, limit=50):
                return [
                    {
                        "version_id": "v-conflict",
                        "timestamp": "2026-05-04 12:00:00",
                        "path": "sessions/sid-1/memory.md",
                        "scope_id": "sid-1",
                        "source_session_id": "sid-1",
                        "metadata": {
                            "conflict_status": "pending_review",
                            "conflict": {
                                "reason": "相反判断",
                                "existing_preview": "旧记忆",
                            },
                        },
                    }
                ]

            def read_memory(self, path):
                return {
                    "path": path,
                    "content": self.content,
                    "content_sha256": "sha",
                }

            def update_memory(self, path, content, content_sha256=None, actor="user"):
                self.content = content
                self.updated = (path, content_sha256, actor)
                return {"operation": "modified", "path": path, "metadata": {"actor": actor}}

        db = MemoryDB.__new__(MemoryDB)
        db.file_memory_store = FakeConflictStore()

        pending = MemoryDB.list_pending_memory_conflicts(db)
        resolved = MemoryDB.resolve_pending_memory_conflict(db, "v-conflict", "keep_old")

        self.assertEqual(pending[0]["version_id"], "v-conflict")
        self.assertEqual(pending[0]["existing_preview"], "旧记忆")
        self.assertEqual(resolved["operation"], "modified")
        self.assertIn("已保留旧记忆", db.file_memory_store.content)


if __name__ == "__main__":
    unittest.main()
