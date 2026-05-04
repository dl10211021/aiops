import asyncio
import unittest
import warnings
from unittest.mock import patch

from fastapi import HTTPException

from api import knowledge_routes, routes
from core.knowledge_base_service import KnowledgeBaseServiceError


warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)


class TestKnowledgeRoutes(unittest.TestCase):
    def test_knowledge_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/knowledge/memory/list", paths)
        self.assertIn("/knowledge/memory/read", paths)
        self.assertIn("/knowledge/memory/search", paths)
        self.assertIn("/knowledge/memory", paths)
        self.assertIn("/knowledge/memory/versions", paths)
        self.assertIn("/knowledge/memory/pending", paths)
        self.assertIn("/knowledge/memory/pending/resolve", paths)
        self.assertIn("/knowledge/memory/review", paths)
        self.assertIn("/knowledge/memory/review/confirm", paths)
        self.assertIn("/knowledge/memory/stores", paths)
        self.assertIn("/knowledge/memory/restore", paths)
        self.assertIn("/knowledge/memory/versions/redact", paths)
        self.assertIn("/knowledge/memory/export", paths)
        self.assertIn("/knowledge/upload", paths)
        self.assertIn("/knowledge/list", paths)
        self.assertIn("/knowledge/vault/queue", paths)
        self.assertIn("/knowledge/vault/compile", paths)
        self.assertIn("/knowledge/vault/candidates", paths)
        self.assertIn("/knowledge/vault/approve", paths)
        self.assertIn("/knowledge/{filename}", paths)

    def test_upload_knowledge_document_preserves_response_shape(self):
        upload = object()

        with patch(
            "api.knowledge_routes.ingest_knowledge_document",
            return_value="注入成功",
        ):
            response = asyncio.run(knowledge_routes.upload_knowledge_document(upload))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "注入成功")

    def test_list_knowledge_documents_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.list_knowledge_document_records",
            return_value=["runbook.txt"],
        ):
            response = asyncio.run(knowledge_routes.list_knowledge_documents())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"files": ["runbook.txt"]})

    def test_list_knowledge_vault_queue_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.list_vault_compile_queue",
            return_value=[{"id": "src-1", "source_session_id": "source-session-1"}],
        ):
            response = asyncio.run(knowledge_routes.list_knowledge_vault_queue())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"items": [{"id": "src-1", "source_session_id": "source-session-1"}]})

    def test_compile_knowledge_vault_source_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.compile_vault_source_candidate",
            return_value={"id": "src-1", "candidate_path": "wiki/candidates/runbook.md"},
        ):
            response = asyncio.run(
                knowledge_routes.compile_knowledge_vault_source(
                    knowledge_routes.KnowledgeVaultCompileRequest(
                        source_session_id="source-session-1",
                        use_ai=False,
                    )
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "候选 Wiki 页面已生成")
        self.assertEqual(response.data, {"item": {"id": "src-1", "candidate_path": "wiki/candidates/runbook.md"}})

    def test_list_and_approve_knowledge_vault_candidates_preserve_response_shape(self):
        with patch(
            "api.knowledge_routes.list_vault_candidates",
            return_value=[{"id": "src-1", "candidate_path": "wiki/candidates/runbook.md"}],
        ):
            list_response = asyncio.run(knowledge_routes.list_knowledge_vault_candidates())

        with patch(
            "api.knowledge_routes.approve_vault_candidate",
            return_value={"id": "src-1", "wiki_path": "wiki/articles/runbook.md"},
        ):
            approve_response = asyncio.run(
                knowledge_routes.approve_knowledge_vault_candidate(
                    knowledge_routes.KnowledgeVaultApproveRequest(
                        source_session_id="source-session-1",
                    )
                )
            )

        self.assertEqual(list_response.status, "success")
        self.assertEqual(list_response.data, {"items": [{"id": "src-1", "candidate_path": "wiki/candidates/runbook.md"}]})
        self.assertEqual(approve_response.status, "success")
        self.assertEqual(approve_response.message, "候选 Wiki 已批准入库")
        self.assertEqual(approve_response.data, {"item": {"id": "src-1", "wiki_path": "wiki/articles/runbook.md"}})

    def test_delete_knowledge_document_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.remove_knowledge_document_record",
            return_value="已成功从知识库中移除 runbook.txt",
        ):
            response = asyncio.run(knowledge_routes.delete_knowledge_document("runbook.txt"))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "已成功从知识库中移除 runbook.txt")

    def test_memory_management_routes_preserve_response_shapes(self):
        class FakeFileMemoryStore:
            def list_memories(self):
                return [{"path": "sessions/sid-1/memory.md"}]

            def list_stores(self):
                return [{"id": "sessions", "access": "read_write"}]

            def read_memory(self, path):
                return {"path": path, "content": "# memory", "content_sha256": "sha"}

            def append_memory(self, scope_id, summary, source_session_id, metadata=None):
                self.created = (scope_id, summary, source_session_id, metadata)
                return {"version_id": "created-v1", "operation": "created", "path": "sessions/manual/memory.md"}

            def search(self, scope_ids, query, limit=6):
                self.searched = (scope_ids, query, limit)
                return [{"path": "sessions/manual/memory.md", "summary": "命中记忆"}]

            def update_memory(self, path, content, content_sha256=None):
                self.updated = (path, content, content_sha256)

            def delete_memory(self, path):
                self.deleted = path

            def restore_version(self, version_id):
                return {"version_id": version_id, "operation": "restored"}

            def redact_version(self, version_id):
                self.redacted = version_id
                return {"version_id": version_id, "operation": "created", "redacted": True}

            def mark_reviewed(self, path, actor="user"):
                self.reviewed = (path, actor)
                return {"version_id": "review-v1", "operation": "modified"}

            def export_store(self):
                return {"stores": [{"id": "sessions"}], "memories": [], "versions": []}

            def list_versions(self, limit=50):
                self.limit = limit
                return [{"version_id": "v1", "operation": "created", "path": "sessions/sid-1/memory.md"}]

        class FakeMemoryDB:
            file_memory_store = FakeFileMemoryStore()

            def list_pending_memory_conflicts(self, limit=50):
                self.pending_limit = limit
                return [{"version_id": "v-pending", "path": "sessions/sid-1/memory.md"}]

            def list_memory_review_items(self, stale_days=180, limit=50):
                self.review_limit = (stale_days, limit)
                return [{"path": "sessions/sid-1/memory.md", "age_days": 181}]

            def resolve_pending_memory_conflict(self, version_id, action):
                self.resolved = (version_id, action)
                return {"version_id": version_id, "operation": "modified"}

            def mark_memory_reviewed(self, path):
                return self.file_memory_store.mark_reviewed(path, actor="user")

        fake_db = FakeMemoryDB()
        with patch("core.memory.memory_db", fake_db):
            stores_response = asyncio.run(knowledge_routes.list_memory_stores())
            list_response = asyncio.run(knowledge_routes.list_memory_items())
            read_response = asyncio.run(knowledge_routes.read_memory_item("sessions/sid-1/memory.md"))
            create_response = asyncio.run(
                knowledge_routes.create_memory_item(
                    knowledge_routes.MemoryCreateRequest(
                        scope_id="manual",
                        summary="【核心记忆】手工写入。",
                    )
                )
            )
            search_response = asyncio.run(
                knowledge_routes.search_memory_items(
                    knowledge_routes.MemorySearchRequest(
                        query="SSH 高频登录",
                        scope_ids=["manual"],
                        limit=3,
                    )
                )
            )
            versions_response = asyncio.run(knowledge_routes.list_memory_versions(10))
            pending_response = asyncio.run(knowledge_routes.list_memory_pending_conflicts(20))
            review_response = asyncio.run(knowledge_routes.list_memory_review_items(180, 20))
            update_response = asyncio.run(
                knowledge_routes.update_memory_item(
                    knowledge_routes.MemoryUpdateRequest(content="# changed", content_sha256="sha"),
                    "sessions/sid-1/memory.md",
                )
            )
            restore_response = asyncio.run(
                knowledge_routes.restore_memory_version(
                    knowledge_routes.MemoryRestoreRequest(version_id="v1")
                )
            )
            redact_response = asyncio.run(
                knowledge_routes.redact_memory_version(
                    knowledge_routes.MemoryVersionRedactRequest(version_id="v1")
                )
            )
            export_response = asyncio.run(knowledge_routes.export_memory_store())
            resolve_response = asyncio.run(
                knowledge_routes.resolve_memory_pending_conflict(
                    knowledge_routes.MemoryConflictResolveRequest(version_id="v-pending", action="accept_new")
                )
            )
            review_confirm_response = asyncio.run(
                knowledge_routes.confirm_memory_review(
                    knowledge_routes.MemoryReviewConfirmRequest(path="sessions/sid-1/memory.md")
                )
            )
            delete_response = asyncio.run(knowledge_routes.delete_memory_item("sessions/sid-1/memory.md"))

        self.assertEqual(stores_response.data, {"stores": [{"id": "sessions", "access": "read_write"}]})
        self.assertEqual(list_response.data, {"items": [{"path": "sessions/sid-1/memory.md"}]})
        self.assertEqual(read_response.data, {"item": {"path": "sessions/sid-1/memory.md", "content": "# memory", "content_sha256": "sha"}})
        self.assertEqual(create_response.message, "记忆已创建")
        self.assertEqual(fake_db.file_memory_store.created[0], "manual")
        self.assertEqual(search_response.data, {"results": [{"path": "sessions/manual/memory.md", "summary": "命中记忆"}]})
        self.assertEqual(fake_db.file_memory_store.searched, (["manual"], "SSH 高频登录", 3))
        self.assertEqual(versions_response.data, {"versions": [{"version_id": "v1", "operation": "created", "path": "sessions/sid-1/memory.md"}]})
        self.assertEqual(pending_response.data, {"items": [{"version_id": "v-pending", "path": "sessions/sid-1/memory.md"}]})
        self.assertEqual(review_response.data, {"items": [{"path": "sessions/sid-1/memory.md", "age_days": 181}]})
        self.assertEqual(update_response.message, "记忆已更新")
        self.assertEqual(restore_response.message, "记忆版本已恢复")
        self.assertEqual(redact_response.message, "记忆版本已脱敏")
        self.assertEqual(fake_db.file_memory_store.redacted, "v1")
        self.assertEqual(resolve_response.message, "待确认记忆已处理")
        self.assertEqual(review_confirm_response.message, "记忆已标记为复核通过")
        self.assertEqual(fake_db.resolved, ("v-pending", "accept_new"))
        self.assertEqual(export_response.data, {"export": {"stores": [{"id": "sessions"}], "memories": [], "versions": []}})
        self.assertEqual(delete_response.message, "记忆已删除: sessions/sid-1/memory.md")

    def test_knowledge_route_errors_keep_http_semantics(self):
        with patch(
            "api.knowledge_routes.list_knowledge_document_records",
            side_effect=KnowledgeBaseServiceError(404, "知识库为空"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(knowledge_routes.list_knowledge_documents())

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "知识库为空")


if __name__ == "__main__":
    unittest.main()
