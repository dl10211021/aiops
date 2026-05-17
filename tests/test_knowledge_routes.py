import asyncio
import tempfile
import unittest
import warnings
from unittest.mock import patch

from fastapi import HTTPException
from starlette.responses import FileResponse
from pathlib import Path

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
        self.assertIn("/knowledge/document", paths)
        self.assertIn("/knowledge/document/reindex", paths)
        self.assertIn("/knowledge/vault/queue", paths)
        self.assertIn("/knowledge/vault/compile", paths)
        self.assertIn("/knowledge/vault/candidates", paths)
        self.assertIn("/knowledge/vault/search", paths)
        self.assertIn("/knowledge/vault/graph", paths)
        self.assertIn("/knowledge/vault/export", paths)
        self.assertIn("/knowledge/vault/import", paths)
        self.assertIn("/knowledge/vault/candidate", paths)
        self.assertIn("/knowledge/vault/approve", paths)
        self.assertIn("/knowledge/vault/articles", paths)
        self.assertIn("/knowledge/vault/article", paths)
        self.assertIn("/knowledge/memory/learning-candidates/{candidate_id}/artifact", paths)
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
            "api.knowledge_routes.list_knowledge_document_page",
            return_value={
                "files": [{"filename": "runbook.txt"}],
                "summary": {"total": 1, "filtered": 1, "vector_counts": {"indexed": 1}},
                "pagination": {"page": 1, "per_page": 50, "total": 1, "page_count": 1, "has_prev": False, "has_next": False},
                "vector_store": {"status": "ready", "database": "LanceDB"},
            },
        ):
            response = asyncio.run(
                knowledge_routes.list_knowledge_documents(
                    q="",
                    vector_status="all",
                    extension="all",
                    page=1,
                    per_page=50,
                    sort="updated_desc",
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["files"], [{"filename": "runbook.txt"}])
        self.assertEqual(response.data["summary"]["total"], 1)
        self.assertEqual(response.data["pagination"]["page"], 1)
        self.assertEqual(response.data["vector_store"]["database"], "LanceDB")

    def test_read_knowledge_document_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.read_knowledge_document_record",
            return_value={"filename": "runbook.txt", "content": "CPU 正常", "preview_available": True},
        ):
            response = asyncio.run(knowledge_routes.read_knowledge_document("runbook.txt"))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"item": {"filename": "runbook.txt", "content": "CPU 正常", "preview_available": True}})

    def test_reindex_knowledge_document_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.reindex_knowledge_document_record",
            return_value={"filename": "runbook.txt", "vector_status": "indexed", "message": "资料向量索引已重建"},
        ):
            response = asyncio.run(
                knowledge_routes.reindex_knowledge_document(
                    knowledge_routes.KnowledgeDocumentReindexRequest(filename="runbook.txt")
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "资料向量索引已重建")
        self.assertEqual(response.data["item"]["vector_status"], "indexed")

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
        self.assertEqual(response.message, "AI 摘要页面已生成")
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
        self.assertEqual(approve_response.message, "AI 摘要已批准入库")
        self.assertEqual(approve_response.data, {"item": {"id": "src-1", "wiki_path": "wiki/articles/runbook.md"}})

    def test_read_and_update_knowledge_vault_candidate_preserve_response_shape(self):
        with patch(
            "api.knowledge_routes.read_vault_candidate",
            return_value={"id": "src-1", "content": "# candidate", "content_sha256": "sha"},
        ):
            read_response = asyncio.run(knowledge_routes.read_knowledge_vault_candidate("source-session-1"))

        with patch(
            "api.knowledge_routes.update_vault_candidate",
            return_value={"id": "src-1", "content": "# changed", "content_sha256": "sha2"},
        ):
            update_response = asyncio.run(
                knowledge_routes.update_knowledge_vault_candidate(
                    knowledge_routes.KnowledgeVaultCandidateUpdateRequest(
                        source_session_id="source-session-1",
                        content="# changed",
                        content_sha256="sha",
                    )
                )
            )

        self.assertEqual(read_response.status, "success")
        self.assertEqual(read_response.data, {"item": {"id": "src-1", "content": "# candidate", "content_sha256": "sha"}})
        self.assertEqual(update_response.status, "success")
        self.assertEqual(update_response.message, "AI 摘要已保存")
        self.assertEqual(update_response.data, {"item": {"id": "src-1", "content": "# changed", "content_sha256": "sha2"}})

    def test_list_and_read_knowledge_vault_articles_preserve_response_shape(self):
        with patch(
            "api.knowledge_routes.list_vault_articles",
            return_value=[{"id": "src-1", "wiki_path": "wiki/articles/runbook.md"}],
        ):
            list_response = asyncio.run(knowledge_routes.list_knowledge_vault_articles())

        with patch(
            "api.knowledge_routes.read_vault_article",
            return_value={"id": "src-1", "content": "# article", "content_sha256": "sha"},
        ):
            read_response = asyncio.run(knowledge_routes.read_knowledge_vault_article("source-session-1"))

        self.assertEqual(list_response.status, "success")
        self.assertEqual(list_response.data, {"items": [{"id": "src-1", "wiki_path": "wiki/articles/runbook.md"}]})
        self.assertEqual(read_response.status, "success")
        self.assertEqual(read_response.data, {"item": {"id": "src-1", "content": "# article", "content_sha256": "sha"}})

    def test_search_knowledge_vault_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.search_vault_knowledge",
            return_value=[
                {
                    "id": "src-1",
                    "title": "Linux 巡检",
                    "kind": "articles",
                    "kind_label": "RAG 资料",
                    "path": "wiki/articles/linux.md",
                    "snippet": "CPU 正常",
                    "score": 2,
                }
            ],
        ):
            response = asyncio.run(
                knowledge_routes.search_knowledge_vault(
                    knowledge_routes.KnowledgeVaultSearchRequest(
                        query="CPU",
                        scope="all",
                        limit=5,
                    )
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["results"][0]["kind_label"], "RAG 资料")
        self.assertEqual(response.data["results"][0]["snippet"], "CPU 正常")

    def test_graph_knowledge_vault_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.build_vault_knowledge_graph",
            return_value={
                "nodes": [{"id": "wiki/articles/linux.md", "title": "Linux", "kind": "article", "x": 50, "y": 50, "degree": 0}],
                "edges": [],
                "summary": {
                    "node_count": 1,
                    "edge_count": 0,
                    "article_count": 1,
                    "candidate_count": 0,
                    "linked_node_count": 0,
                    "isolated_node_count": 1,
                    "relation_counts": {},
                },
            },
        ):
            response = asyncio.run(
                knowledge_routes.graph_knowledge_vault(
                    knowledge_routes.KnowledgeVaultGraphRequest(include_candidates=False)
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data["summary"]["article_count"], 1)
        self.assertEqual(response.data["summary"]["isolated_node_count"], 1)
        self.assertEqual(response.data["nodes"][0]["title"], "Linux")
        self.assertEqual(response.data["nodes"][0]["x"], 50)

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

            def analyze_quality(
                self,
                stale_days=180,
                pending_conflicts=None,
                recent_versions=None,
                max_candidates=8,
            ):
                self.quality_args = (stale_days, pending_conflicts, recent_versions, max_candidates)
                return {
                    "summary": {
                        "memory_count": 1,
                        "entry_count": 13,
                        "store_count": 1,
                        "pending_conflict_count": len(pending_conflicts or []),
                        "stale_review_count": 1,
                        "compression_candidate_count": 1,
                        "duplicate_entry_count": 0,
                        "recent_version_count": len(recent_versions or []),
                        "health_score": 82,
                    },
                    "stores": [{"store_id": "sessions", "store_name": "会话记忆", "memories": 1, "entries": 13, "size": 2048}],
                    "compression_candidates": [
                        {
                            "path": "sessions/sid-1/memory.md",
                            "store_id": "sessions",
                            "store_name": "会话记忆",
                            "entries": 13,
                            "size": 2048,
                            "priority": "high",
                            "score": 50,
                            "reason": "条目较多",
                            "recommended_action": "生成压缩草稿",
                        }
                    ],
                    "policy": {"mode": "candidate_only", "stale_days": stale_days, "auto_apply": False, "rule": "只生成候选，不自动覆盖。"},
                }

            def list_candidate_entries(self, limit=50, review_statuses=None):
                self.candidate_limit = limit
                self.candidate_review_statuses = review_statuses
                return [{"candidate_id": "memcand_1", "path": "sessions/sid-1/memory.md", "review_status": "pending"}]

            def list_learning_candidates(self, limit=50, target_type="", statuses=None):
                self.learning_candidate_query = (limit, target_type, statuses)
                if not hasattr(self, "learning_candidate_queries"):
                    self.learning_candidate_queries = []
                self.learning_candidate_queries.append(self.learning_candidate_query)
                return [{"id": "learncand_1", "target_type": "runbook", "status": "draft"}]

            def update_learning_candidate_status(self, candidate_id, status, actor="user", reason=""):
                self.learning_candidate_status = (candidate_id, status, actor, reason)
                if not hasattr(self, "learning_candidate_statuses"):
                    self.learning_candidate_statuses = []
                self.learning_candidate_statuses.append(self.learning_candidate_status)
                result = {"id": candidate_id, "status": status, "status_events": [{"to": status, "actor": actor, "reason": reason}]}
                if status == "published":
                    result["published_artifact"] = {
                        "artifact_id": "publish_abc123456789",
                        "target_type": "runbook",
                        "file_path": "learning_candidate_publish_artifacts/runbook/publish_abc123456789.md",
                        "status": "draft",
                        "generated_by": actor,
                        "generated_reason": reason,
                        "generated_at": "2026-05-15 12:00:00",
                        "content_preview": "发布草稿预览文本",
                        "content_sha256": "deadbeef",
                        "artifact_sha256": "deadbeef",
                    }
                return result

            def update_learning_candidate_quality_checklist(self, candidate_id, checklist, actor="user", reason=""):
                self.learning_candidate_quality = (candidate_id, checklist, actor, reason)
                return {"id": candidate_id, "quality_checklist": checklist, "quality_events": [{"actor": actor, "reason": reason}]}

            def resolve_candidate_entry(self, candidate_id, action):
                self.candidate_resolved = (candidate_id, action)
                return {"version_id": "candidate-v1", "operation": "modified"}

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
            candidates_response = asyncio.run(
                knowledge_routes.list_memory_candidates(20, "pending,runbook_candidate,invalid")
            )
            learning_candidates_response = asyncio.run(
                knowledge_routes.list_memory_learning_candidates(12, "runbook", "draft,reviewing,invalid")
            )
            learning_candidate_status_response = asyncio.run(
                knowledge_routes.update_memory_learning_candidate_status(
                    "learncand_1",
                    knowledge_routes.MemoryLearningCandidateStatusRequest(
                        status="reviewing",
                        actor="tester",
                        reason="准备评审",
                    ),
                )
            )
            learning_candidate_publish_response = asyncio.run(
                knowledge_routes.update_memory_learning_candidate_status(
                    "learncand_1",
                    knowledge_routes.MemoryLearningCandidateStatusRequest(
                        status="published",
                        actor="tester",
                        reason="发布草稿已生成",
                    ),
                )
            )
            learning_candidate_quality_response = asyncio.run(
                knowledge_routes.update_memory_learning_candidate_quality_checklist(
                    "learncand_1",
                    knowledge_routes.MemoryLearningCandidateQualityRequest(
                        checklist=[
                            knowledge_routes.MemoryLearningCandidateQualityItem(
                                key="scope",
                                label="适用范围",
                                ok=True,
                                note="已限定 Linux 主机",
                            )
                        ],
                        actor="tester",
                        reason="补齐质量清单",
                    ),
                )
            )
            candidate_resolve_response = asyncio.run(
                knowledge_routes.resolve_memory_candidate(
                    knowledge_routes.MemoryCandidateResolveRequest(
                        candidate_id="memcand_1",
                        action="to_runbook",
                    )
                )
            )
            review_response = asyncio.run(knowledge_routes.list_memory_review_items(180, 20))
            quality_export_response = asyncio.run(knowledge_routes.export_memory_quality_report(180, 8))
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
        self.assertEqual(candidates_response.data, {"items": [{"candidate_id": "memcand_1", "path": "sessions/sid-1/memory.md", "review_status": "pending"}]})
        self.assertEqual(fake_db.file_memory_store.candidate_limit, 20)
        self.assertEqual(fake_db.file_memory_store.candidate_review_statuses, ["pending", "runbook_candidate"])
        self.assertEqual(learning_candidates_response.data, {"items": [{"id": "learncand_1", "target_type": "runbook", "status": "draft"}]})
        self.assertIn((12, "runbook", ["draft", "reviewing"]), fake_db.file_memory_store.learning_candidate_queries)
        self.assertIn((200, "", None), fake_db.file_memory_store.learning_candidate_queries)
        self.assertEqual(learning_candidate_status_response.message, "发布候选状态已更新")
        self.assertEqual(learning_candidate_publish_response.message, "发布候选状态已更新")
        self.assertIn("published_artifact", learning_candidate_publish_response.data["item"])
        self.assertEqual(fake_db.file_memory_store.learning_candidate_status, ("learncand_1", "published", "tester", "发布草稿已生成"))
        self.assertIn(("learncand_1", "reviewing", "tester", "准备评审"), fake_db.file_memory_store.learning_candidate_statuses)
        self.assertIn(("learncand_1", "published", "tester", "发布草稿已生成"), fake_db.file_memory_store.learning_candidate_statuses)
        self.assertEqual(learning_candidate_quality_response.message, "发布质量清单已更新")
        self.assertEqual(fake_db.file_memory_store.learning_candidate_quality[0], "learncand_1")
        self.assertEqual(fake_db.file_memory_store.learning_candidate_quality[1][0]["key"], "scope")
        self.assertEqual(fake_db.file_memory_store.learning_candidate_quality[1][0]["note"], "已限定 Linux 主机")
        self.assertEqual(candidate_resolve_response.message, "候选记忆已处理")
        self.assertEqual(fake_db.file_memory_store.candidate_resolved, ("memcand_1", "to_runbook"))
        self.assertEqual(review_response.data, {"items": [{"path": "sessions/sid-1/memory.md", "age_days": 181}]})
        self.assertEqual(quality_export_response.message, "记忆质量报表已生成")
        self.assertIn("# OpsCore 记忆质量报表", quality_export_response.data["markdown"])
        self.assertIn("## 学习候选", quality_export_response.data["markdown"])
        self.assertIn("sessions/sid-1/memory.md", quality_export_response.data["markdown"])
        self.assertEqual(quality_export_response.data["learning_candidate_stats"]["total"], 1)
        self.assertEqual(fake_db.file_memory_store.quality_args[0], 180)
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
            "api.knowledge_routes.list_knowledge_document_page",
            side_effect=KnowledgeBaseServiceError(404, "知识库为空"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    knowledge_routes.list_knowledge_documents(
                        q="",
                        vector_status="all",
                        extension="all",
                        page=1,
                        per_page=50,
                        sort="updated_desc",
                    )
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "知识库为空")

    def test_read_learning_candidate_publish_artifact_route_returns_model(self):
        class FakeFileMemoryStore:
            def read_learning_candidate_publish_artifact(self, candidate_id):
                return {
                    "candidate_id": candidate_id,
                    "artifact_id": "publish_abc123456789",
                    "target_type": "runbook",
                    "file_path": "learning_candidate_publish_artifacts/runbook/publish_abc123456789.md",
                    "status": "draft",
                    "generated_by": "tester",
                    "generated_reason": "发布草稿已生成",
                    "generated_at": "2026-05-15 12:34:56",
                    "content_preview": "发布草稿预览",
                    "artifact_sha256": "deadbeef",
                    "content_sha256": "deadbeef",
                    "content": "# 发布草稿\n内容正文",
                }

        class FakeMemoryDB:
            file_memory_store = FakeFileMemoryStore()

        with patch("core.memory.memory_db", FakeMemoryDB()):
            response = asyncio.run(
                knowledge_routes.read_learning_candidate_publish_artifact(
                    "learncand_1",
                    download=False,
                )
            )

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "发布草稿读取成功")
        self.assertEqual(response.data["artifact"]["candidate_id"], "learncand_1")
        self.assertEqual(response.data["artifact"]["artifact_id"], "publish_abc123456789")

    def test_download_learning_candidate_publish_artifact_route_returns_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            artifact_file = Path(tempdir) / "publish_abc123456789.md"
            artifact_file.write_text("发布草稿内容", encoding="utf-8")
            class FakeFileMemoryStore:
                def read_learning_candidate_publish_artifact(self, candidate_id):
                    return {
                        "candidate_id": candidate_id,
                        "artifact_id": "publish_abc123456789",
                        "target_type": "runbook",
                        "file_path": "learning_candidate_publish_artifacts/runbook/publish_abc123456789.md",
                        "status": "draft",
                        "generated_by": "tester",
                        "generated_reason": "发布草稿已生成",
                        "generated_at": "2026-05-15 12:34:56",
                        "content_preview": "发布草稿预览",
                        "artifact_sha256": "deadbeef",
                        "content_sha256": "deadbeef",
                    }

                def resolve_learning_candidate_publish_artifact_path(self, file_path):
                    return artifact_file

            class FakeMemoryDB:
                file_memory_store = FakeFileMemoryStore()

            with patch("core.memory.memory_db", FakeMemoryDB()):
                response = asyncio.run(
                    knowledge_routes.read_learning_candidate_publish_artifact(
                        "learncand_2",
                        download=True,
                    )
                )

        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.filename, "publish_abc123456789.md")


if __name__ == "__main__":
    unittest.main()
