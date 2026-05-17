import json
import shutil
import unittest
import uuid
import os
import time
from pathlib import Path

from core.file_memory_store import (
    FileMemoryStore,
    is_legacy_shared_memory_scope,
    memory_scope_path,
    safe_memory_segment,
)


class FileMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_file_memory_{uuid.uuid4().hex}"
        self.store = FileMemoryStore(self.tmp_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_append_memory_writes_markdown_and_version_log(self):
        version = self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】纠错经验\n【核心记忆】不要直接建议 ufw enable。",
            source_session_id="sid-1",
            metadata={"source": "feedback"},
        )

        memory_path = self.tmp_path / "sessions" / "sid-1" / "memory.md"
        version_files = list((self.tmp_path / "versions").glob("*.jsonl"))

        self.assertTrue(memory_path.exists())
        self.assertEqual(version["operation"], "created")
        self.assertEqual(version["path"], "sessions/sid-1/memory.md")
        self.assertEqual(len(version_files), 1)
        self.assertIn("不要直接建议 ufw enable", memory_path.read_text(encoding="utf-8"))

        events = [
            json.loads(line)
            for line in version_files[0].read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(events[0]["operation"], "created")
        self.assertEqual(events[0]["source_session_id"], "sid-1")
        self.assertEqual(events[0]["metadata"]["memory_model"], "hermes_style_session_retention")
        self.assertEqual(events[0]["metadata"]["memory_kind"], "error_feedback")
        self.assertEqual(events[0]["metadata"]["retention_tier"], "negative_learning")
        self.assertTrue(events[0]["metadata"]["retrieval_enabled"])

    def test_search_returns_relevant_scope_entries_without_duplicates(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】Linux 巡检需要先看 systemctl failed。",
            source_session_id="sid-1",
        )
        self.store.append_memory(
            scope_id="sid-2",
            summary="【核心记忆】Oracle 资产优先检查活跃会话和锁等待。",
            source_session_id="sid-2",
        )

        results = self.store.search(
            scope_ids=["sid-1", "sid-2"],
            query="Oracle 锁等待",
            limit=2,
        )

        self.assertEqual(results[0]["_memory_scope_id"], "sid-2")
        self.assertIn("Oracle", results[0]["summary"])
        self.assertEqual(results[0]["memory_model"], "hermes_style_session_retention")
        self.assertEqual(results[0]["memory_kind"], "session_state")
        self.assertEqual(len(results), 2)

    def test_search_excludes_audit_archive_entries_but_list_keeps_them(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】会话状态\n【核心记忆】Oracle 锁等待排查继续看 v$session。",
            source_session_id="sid-1",
        )
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】复核记录\n【复核状态】已复核\n【核心记忆】仅用于审计。",
            source_session_id="sid-1",
            metadata={"source": "memory_review"},
        )

        results = self.store.search(scope_ids=["sid-1"], query="复核 审计 Oracle", limit=5)
        item = self.store.list_memories()[0]
        detail = self.store.read_memory(item["path"])

        self.assertEqual(len(results), 1)
        self.assertIn("Oracle", results[0]["summary"])
        self.assertEqual(results[0]["memory_kind"], "session_state")
        self.assertEqual(item["entries"], 2)
        self.assertEqual(item["retrieval_entries"], 1)
        self.assertEqual(item["audit_entries"], 1)
        self.assertEqual(item["entry_kinds"]["audit_archive"], 1)
        self.assertEqual(detail["audit_entries"], 1)

    def test_mark_reviewed_promotes_pending_candidate_entries(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="\n".join(
                [
                    "【记忆类型】用户认可回答",
                    "【候选状态】待人工确认",
                    "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
                    "【核心记忆】Oracle 巡检报告结构清晰。",
                    "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。",
                ]
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
            },
        )

        self.assertEqual(
            self.store.search(scope_ids=["sid-1"], query="Oracle 巡检", limit=5),
            [],
        )

        self.store.mark_reviewed("sessions/sid-1/memory.md")

        detail = self.store.read_memory("sessions/sid-1/memory.md")
        self.assertIn('"review_status": "confirmed"', detail["content"])
        self.assertIn('"retrieval_enabled": true', detail["content"])
        self.assertIn("【候选状态】已人工确认", detail["content"])
        results = self.store.search(scope_ids=["sid-1"], query="Oracle 巡检", limit=5)
        self.assertEqual(len(results), 1)
        self.assertIn("Oracle 巡检报告结构清晰", results[0]["summary"])

    def test_list_candidate_entries_returns_pending_review_items_only(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】用户认可回答\n【候选状态】待人工确认\n【核心记忆】候选经验。",
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "candidate_type": "feedback_success_experience",
                "retrieval_enabled": False,
                "feedback_target_message_id": 7,
                "evidence_refs": [
                    {
                        "type": "tool_evidence",
                        "label": "工具证据",
                        "id": "tev-sid-1-call-1",
                        "tool": "linux_execute_command",
                        "status": "done",
                    }
                ],
            },
        )
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】用户纠错反馈\n【核心记忆】纠错经验。",
            source_session_id="sid-1",
            metadata={"review_status": "confirmed"},
        )

        candidates = self.store.list_candidate_entries(limit=10)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["path"], "sessions/sid-1/memory.md")
        self.assertEqual(candidates[0]["candidate_type"], "feedback_success_experience")
        self.assertEqual(candidates[0]["review_status"], "pending")
        self.assertFalse(candidates[0]["retrieval_enabled"])
        self.assertEqual(candidates[0]["feedback_target_message_id"], 7)
        self.assertTrue(candidates[0]["candidate_id"].startswith("memcand_"))
        self.assertIn({"type": "session", "label": "来源会话", "id": "sid-1"}, candidates[0]["source_refs"])
        self.assertIn({"type": "message", "label": "反馈消息", "id": "7"}, candidates[0]["source_refs"])
        self.assertIn({"type": "memory_file", "label": "记忆文件", "path": "sessions/sid-1/memory.md"}, candidates[0]["source_refs"])
        self.assertEqual(candidates[0]["evidence_refs"][0]["id"], "tev-sid-1-call-1")
        self.assertEqual(candidates[0]["evidence_refs"][0]["tool"], "linux_execute_command")

    def test_resolve_candidate_entry_confirms_single_candidate(self):
        for label in ("第一条候选", "第二条候选"):
            self.store.append_memory(
                scope_id="sid-1",
                summary=f"【记忆类型】用户认可回答\n【候选状态】待人工确认\n【核心记忆】{label}。",
                source_session_id="sid-1",
                metadata={
                    "source": "answer_feedback_candidate",
                    "memory_kind": "success_experience",
                    "review_status": "pending",
                    "retrieval_enabled": False,
                },
            )
        candidates = self.store.list_candidate_entries(limit=10)
        target = next(item for item in candidates if "第一条候选" in item["summary"])

        version = self.store.resolve_candidate_entry(target["candidate_id"], "confirm")

        self.assertEqual(version["operation"], "modified")
        remaining = self.store.list_candidate_entries(limit=10)
        self.assertEqual(len(remaining), 1)
        self.assertIn("第二条候选", remaining[0]["summary"])
        detail = self.store.read_memory("sessions/sid-1/memory.md")
        self.assertIn("第一条候选", detail["content"])
        self.assertIn("【候选状态】已人工确认", detail["content"])
        self.assertIn("第二条候选", detail["content"])
        self.assertIn("【候选状态】待人工确认", detail["content"])

    def test_resolve_candidate_entry_rejects_without_enabling_retrieval(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】用户认可回答\n【候选状态】待人工确认\n【核心记忆】不应沉淀。",
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]

        self.store.resolve_candidate_entry(candidate["candidate_id"], "reject")

        self.assertEqual(self.store.list_candidate_entries(limit=10), [])
        detail = self.store.read_memory("sessions/sid-1/memory.md")
        self.assertIn('"review_status": "rejected"', detail["content"])
        self.assertIn('"retrieval_enabled": false', detail["content"])
        self.assertIn("【候选状态】已拒绝", detail["content"])
        self.assertEqual(
            self.store.search(scope_ids=["sid-1"], query="不应沉淀", limit=5),
            [],
        )

    def test_resolve_candidate_entry_converts_to_runbook_candidate_without_retrieval(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary=(
                "【记忆类型】用户认可回答\n"
                "【候选状态】待人工确认\n"
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。\n"
                "【核心记忆】可以整理成 Runbook。\n"
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。"
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "candidate_type": "feedback_success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
                "run_id": "run-abc",
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]

        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_runbook")

        self.assertEqual(self.store.list_candidate_entries(limit=10), [])
        learning_candidates = self.store.list_learning_candidates(limit=10)
        self.assertEqual(len(learning_candidates), 1)
        self.assertEqual(learning_candidates[0]["target_type"], "runbook")
        self.assertEqual(learning_candidates[0]["status"], "draft")
        self.assertEqual(learning_candidates[0]["run_id"], "run-abc")
        self.assertEqual(learning_candidates[0]["source_candidate_id"], candidate["candidate_id"])
        self.assertIn("Runbook 草稿", learning_candidates[0]["next_action"])
        self.assertEqual(learning_candidates[0]["status_events"][0]["to"], "draft")
        checklist = {row["key"]: row for row in learning_candidates[0]["quality_checklist"]}
        self.assertIn("source_message", checklist)
        self.assertIn("tool_evidence", checklist)
        self.assertIn("evidence_action", checklist)
        self.assertFalse(checklist["evidence_action"]["ok"])
        self.assertIn("steps", checklist)
        self.assertIn("rollback", checklist)
        updated_candidate = self.store.update_learning_candidate_status(
            learning_candidates[0]["id"],
            status="reviewing",
            actor="tester",
            reason="准备评审",
        )
        self.assertEqual(updated_candidate["status"], "reviewing")
        self.assertEqual(updated_candidate["status_events"][-1]["from"], "draft")
        self.assertEqual(updated_candidate["status_events"][-1]["reason"], "准备评审")
        with self.assertRaisesRegex(ValueError, "质量清单未全部通过"):
            self.store.update_learning_candidate_status(
                learning_candidates[0]["id"],
                status="approved",
                actor="tester",
                reason="尝试批准",
            )
        updated_quality = self.store.update_learning_candidate_quality_checklist(
            learning_candidates[0]["id"],
            checklist=[
                {**row, "ok": True, "note": "已补齐"}
                for row in learning_candidates[0]["quality_checklist"]
            ],
            actor="tester",
            reason="补齐发布前检查项",
        )
        self.assertTrue(all(row["ok"] for row in updated_quality["quality_checklist"]))
        self.assertEqual(updated_quality["quality_events"][-1]["passed"], len(updated_quality["quality_checklist"]))
        self.assertEqual(updated_quality["quality_events"][-1]["reason"], "补齐发布前检查项")
        approved_candidate = self.store.update_learning_candidate_status(
            learning_candidates[0]["id"],
            status="approved",
            actor="tester",
            reason="质量清单已通过",
        )
        self.assertEqual(approved_candidate["status"], "approved")
        published_candidate = self.store.update_learning_candidate_status(
            learning_candidates[0]["id"],
            status="published",
            actor="tester",
            reason="已完成发布草稿生成",
        )
        self.assertEqual(published_candidate["status"], "published")
        published_artifact = published_candidate["published_artifact"]
        self.assertIsInstance(published_artifact, dict)
        self.assertEqual(published_artifact.get("status"), "draft")
        self.assertEqual(published_artifact.get("generated_by"), "tester")
        self.assertEqual(published_artifact.get("generated_reason"), "已完成发布草稿生成")
        self.assertIn("content_preview", published_artifact)
        self.assertIn("content_sha256", published_artifact)
        self.assertIn("artifact_sha256", published_artifact)
        artifact_file = self.tmp_path / published_artifact["file_path"]
        self.assertTrue(artifact_file.exists())
        artifact_content = artifact_file.read_text(encoding="utf-8")
        self.assertIn(str(published_candidate["id"]), artifact_content)
        self.assertIn("发布草稿", artifact_content)
        self.assertIn("## Runbook 草稿模板", artifact_content)
        self.assertIn("### 执行前检查", artifact_content)
        self.assertIn("### 执行步骤", artifact_content)
        self.assertIn("### 回滚方案", artifact_content)
        republish = self.store.update_learning_candidate_status(
            learning_candidates[0]["id"],
            status="published",
            actor="tester",
            reason="发布草稿内容更新",
        )
        self.assertEqual(republish["published_artifact"]["artifact_id"], published_artifact["artifact_id"])

        runbook_candidates = self.store.list_candidate_entries(
            limit=10,
            review_statuses=["runbook_candidate"],
        )
        self.assertEqual(len(runbook_candidates), 1)
        self.assertEqual(runbook_candidates[0]["review_status"], "runbook_candidate")
        self.assertEqual(runbook_candidates[0]["candidate_type"], "runbook_candidate")
        self.assertIn("Runbook", runbook_candidates[0]["recommended_action"])
        detail = self.store.read_memory("sessions/sid-1/memory.md")
        self.assertIn('"review_status": "runbook_candidate"', detail["content"])
        self.assertIn('"candidate_type": "runbook_candidate"', detail["content"])
        self.assertIn('"retrieval_enabled": false', detail["content"])
        self.assertIn("【候选状态】已转 Runbook 候选", detail["content"])
        self.assertEqual(
            self.store.search(scope_ids=["sid-1"], query="可以整理成 Runbook", limit=5),
            [],
        )

    def test_resolve_candidate_entry_converts_to_skill_candidate_without_retrieval(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary=(
                "【记忆类型】用户认可回答\n"
                "【候选状态】待人工确认\n"
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。\n"
                "【核心记忆】可以整理成 Skill。\n"
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。"
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "candidate_type": "feedback_success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]

        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_skill")

        self.assertEqual(self.store.list_candidate_entries(limit=10), [])
        learning_candidates = self.store.list_learning_candidates(limit=10, target_type="skill")
        self.assertEqual(len(learning_candidates), 1)
        self.assertEqual(learning_candidates[0]["target_type"], "skill")
        self.assertEqual(learning_candidates[0]["source_candidate_id"], candidate["candidate_id"])
        self.assertIn("Skill 草稿", learning_candidates[0]["next_action"])
        checklist = {row["key"]: row for row in learning_candidates[0]["quality_checklist"]}
        self.assertIn("inputs", checklist)
        self.assertIn("tests", checklist)
        skill_candidates = self.store.list_candidate_entries(
            limit=10,
            review_statuses=["skill_candidate"],
        )
        self.assertEqual(len(skill_candidates), 1)
        self.assertEqual(skill_candidates[0]["review_status"], "skill_candidate")
        self.assertEqual(skill_candidates[0]["candidate_type"], "skill_candidate")
        self.assertIn("Skill", skill_candidates[0]["recommended_action"])
        detail = self.store.read_memory("sessions/sid-1/memory.md")
        self.assertIn('"review_status": "skill_candidate"', detail["content"])
        self.assertIn('"candidate_type": "skill_candidate"', detail["content"])
        self.assertIn('"retrieval_enabled": false', detail["content"])
        self.assertIn("【候选状态】已转 Skill 候选", detail["content"])
        self.assertEqual(
            self.store.search(scope_ids=["sid-1"], query="可以整理成 Skill", limit=5),
            [],
        )

    def test_published_skill_candidate_artifact_uses_skill_template(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary=(
                "【记忆类型】用户认可回答\n"
                "【候选状态】待人工确认\n"
                "【核心记忆】可以整理成 Skill。\n"
                "【使用提醒】人工确认后才可作为当前会话后续参考。"
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "candidate_type": "feedback_success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]
        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_skill")
        learning_candidate = self.store.list_learning_candidates(limit=10, target_type="skill")[0]
        self.store.update_learning_candidate_quality_checklist(
            learning_candidate["id"],
            checklist=[{**row, "ok": True, "note": "已补齐"} for row in learning_candidate["quality_checklist"]],
            actor="tester",
            reason="补齐 Skill 发布前检查项",
        )

        published_candidate = self.store.update_learning_candidate_status(
            learning_candidate["id"],
            status="published",
            actor="tester",
            reason="生成 Skill 发布草稿",
        )

        artifact_file = self.tmp_path / published_candidate["published_artifact"]["file_path"]
        artifact_content = artifact_file.read_text(encoding="utf-8")
        self.assertIn("## Skill 草稿模板", artifact_content)
        self.assertIn("### 建议目录结构", artifact_content)
        self.assertIn("### 输入参数", artifact_content)
        self.assertIn("### 安全边界", artifact_content)
        self.assertIn("validate_skill_candidate", artifact_content)

    def test_update_learning_candidate_status_validates_reason_and_id(self):
        with self.assertRaises(FileNotFoundError):
            self.store.update_learning_candidate_status(
                "missing",
                status="reviewing",
                reason="准备评审",
            )
        self.store.append_memory(
            scope_id="sid-1",
            summary="【记忆类型】用户认可回答\n【候选状态】待人工确认\n【核心记忆】可发布流程。",
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]
        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_runbook")
        learning_candidate = self.store.list_learning_candidates(limit=10)[0]

        with self.assertRaises(ValueError):
            self.store.update_learning_candidate_status(
                learning_candidate["id"],
                status="approved",
                reason="",
            )
        with self.assertRaises(ValueError):
            self.store.update_learning_candidate_status(
                learning_candidate["id"],
                status="bad",
                reason="非法状态",
            )
        with self.assertRaises(ValueError):
            self.store.update_learning_candidate_quality_checklist(
                learning_candidate["id"],
                checklist=[],
                reason="",
            )

    def test_list_read_delete_and_versions_support_management_ui(self):
        self.store.append_memory(
            scope_id="sid-8",
            summary="【核心记忆】巡检前先确认只读模式。",
            source_session_id="sid-8",
        )

        items = self.store.list_memories()
        detail = self.store.read_memory(items[0]["path"])
        deleted = self.store.delete_memory(items[0]["path"], actor="tester")
        versions = self.store.list_versions()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["entries"], 1)
        self.assertEqual(items[0]["memory_model"], "hermes_style_session_retention")
        self.assertEqual(items[0]["retrieval_entries"], 1)
        self.assertEqual(items[0]["entry_kinds"]["session_state"], 1)
        self.assertIn("只读模式", items[0]["preview"])
        self.assertIn("只读模式", detail["content"])
        self.assertEqual(deleted["operation"], "deleted")
        operations = [version["operation"] for version in versions]
        self.assertIn("deleted", operations)
        deleted_versions = [
            version for version in versions if version["operation"] == "deleted"
        ]
        self.assertEqual(deleted_versions[0]["metadata"]["actor"], "tester")
        self.assertEqual(self.store.list_memories(), [])

    def test_legacy_shared_scope_writes_are_rejected(self):
        self.assertTrue(is_legacy_shared_memory_scope("asset-host:10.0.0.8"))
        self.assertTrue(is_legacy_shared_memory_scope("asset-kind:linux:ssh"))
        self.assertFalse(is_legacy_shared_memory_scope("sid-1"))

        with self.assertRaisesRegex(ValueError, "历史共享记忆已归档"):
            self.store.append_memory(
                scope_id="asset-host:10.0.0.8",
                summary="【核心记忆】不应继续写入共享主机记忆。",
                source_session_id="sid-8",
            )

    def test_legacy_shared_files_are_read_only_archive(self):
        self.store.initialize()
        legacy_path = self.tmp_path / "asset_kinds" / "linux_ssh" / "memory.md"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(
            "# OpsCore Memory Store\n\n"
            "- scope_id: asset-kind:linux:ssh\n"
            "- access: read_write\n\n"
            "## 2026-05-05 16:30:01\n"
            "- scope_id: asset-kind:linux:ssh\n"
            "- source_session_id: sid-old\n"
            '- metadata: {"source": "legacy"}\n\n'
            "【核心记忆】旧共享资产类型经验，仅保留审计。\n",
            encoding="utf-8",
        )

        stores = self.store.list_stores()
        item = self.store.list_memories()[0]
        detail = self.store.read_memory(item["path"])

        self.assertEqual(stores[-1]["id"], "legacy_shared")
        self.assertEqual(stores[-1]["access"], "read_only")
        self.assertEqual(item["store_id"], "legacy_shared")
        self.assertEqual(item["access"], "read_only")
        self.assertEqual(item["lifecycle"], "legacy_archived")
        self.assertTrue(item["archived"])
        self.assertFalse(item["retrieval_enabled"])
        self.assertEqual(detail["store_id"], "legacy_shared")
        self.assertTrue(detail["archived"])
        self.assertFalse(detail["retrieval_enabled"])
        with self.assertRaises(PermissionError):
            self.store.update_memory(
                item["path"],
                content=detail["content"] + "\n新内容",
                content_sha256=detail["content_sha256"],
            )
        with self.assertRaises(PermissionError):
            self.store.delete_memory(item["path"], actor="tester")

    def test_read_learning_candidate_publish_artifact_returns_content_and_metadata(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary=(
                "【记忆类型】用户认可回答\n"
                "【候选状态】待人工确认\n"
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。\n"
                "【核心记忆】发布草稿内容。\n"
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。"
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
                "candidate_type": "feedback_success_experience",
                "evidence_refs": [
                    {
                        "type": "tool_evidence",
                        "label": "工具证据",
                        "id": "tev-sid-1-call-1",
                        "tool": "db_execute_query",
                        "status": "done",
                        "evidence_family": "database",
                        "sql_action": "写入/DDL (UPDATE)",
                    },
                    {
                        "type": "tool_evidence",
                        "label": "工具证据",
                        "id": "tev-sid-1-call-2",
                        "tool": "monitoring_api_query",
                        "status": "done",
                        "evidence_family": "observability",
                        "http_action": "只读请求 (GET)",
                    },
                ],
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]
        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_runbook")
        learning_candidate = self.store.list_learning_candidates(limit=10)[0]
        checklist = {row["key"]: row for row in learning_candidate["quality_checklist"]}
        self.assertTrue(checklist["tool_evidence"]["ok"])
        self.assertTrue(checklist["evidence_action"]["ok"])
        updated_quality = self.store.update_learning_candidate_quality_checklist(
            learning_candidate["id"],
            checklist=[
                {**row, "ok": True, "note": "已确认"}
                for row in learning_candidate["quality_checklist"]
            ],
            actor="tester",
            reason="发布前确认清单",
        )
        published = self.store.update_learning_candidate_status(
            learning_candidate["id"],
            status="published",
            actor="tester",
            reason="发布草稿已生成",
        )

        self.assertEqual(published["status"], "published")
        artifact = self.store.read_learning_candidate_publish_artifact(published["id"])

        self.assertEqual(artifact["candidate_id"], published["id"])
        self.assertEqual(artifact["status"], "draft")
        self.assertTrue(artifact["artifact_id"].startswith("publish_"))
        self.assertTrue(artifact["file_path"].startswith("learning_candidate_publish_artifacts/"))
        self.assertEqual(artifact["generated_by"], "tester")
        self.assertEqual(artifact["generated_reason"], "发布草稿已生成")
        self.assertIn("# Runbook 发布草稿", artifact["content"])
        self.assertIn("- evidence_refs: 2", artifact["content"])
        self.assertIn("tev-sid-1-call-1", artifact["content"])
        self.assertIn("  - tool: db_execute_query", artifact["content"])
        self.assertIn("  - action: 写入/DDL (UPDATE)", artifact["content"])
        self.assertIn("  - evidence_family: database", artifact["content"])
        self.assertIn("  - action: 只读请求 (GET)", artifact["content"])
        self.assertEqual(artifact["artifact_size"], len(artifact["content"].encode("utf-8")))
        self.assertTrue(updated_quality["quality_events"][-1]["passed"] >= 1)

    def test_read_learning_candidate_publish_artifact_missing_without_published_artifact(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary=(
                "【记忆类型】用户认可回答\n"
                "【候选状态】待人工确认\n"
                "【核心记忆】未发布前不应读取发布草稿。\n"
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。"
            ),
            source_session_id="sid-1",
            metadata={
                "source": "answer_feedback_candidate",
                "memory_kind": "success_experience",
                "review_status": "pending",
                "retrieval_enabled": False,
                "candidate_type": "feedback_success_experience",
            },
        )
        candidate = self.store.list_candidate_entries(limit=10)[0]
        self.store.resolve_candidate_entry(candidate["candidate_id"], "to_runbook")
        learning_candidate = self.store.list_learning_candidates(limit=10)[0]

        with self.assertRaises(FileNotFoundError):
            self.store.read_learning_candidate_publish_artifact(learning_candidate["id"])

    def test_read_learning_candidate_publish_artifact_rejects_invalid_candidate_id(self):
        with self.assertRaises(ValueError):
            self.store.read_learning_candidate_publish_artifact("   ")

    def test_update_restore_export_and_store_registry(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】原始内容。",
            source_session_id="sid-1",
        )
        item = self.store.list_memories()[0]
        detail = self.store.read_memory(item["path"])

        updated = self.store.update_memory(
            item["path"],
            content=detail["content"] + "\n追加纠错。",
            content_sha256=detail["content_sha256"],
            actor="tester",
        )
        exported = self.store.export_store()
        restored = self.store.restore_version(updated["version_id"], actor="tester")

        self.assertEqual(item["store_id"], "sessions")
        self.assertEqual(item["access"], "read_write")
        self.assertIn("instructions", exported["stores"][0])
        self.assertEqual(updated["operation"], "modified")
        self.assertIn("追加纠错", self.store.read_memory(item["path"])["content"])
        self.assertEqual(restored["operation"], "restored")
        self.assertEqual(exported["stores"][0]["id"], "sessions")
        self.assertTrue(exported["memories"])
        self.assertTrue(exported["versions"])

    def test_update_memory_rejects_stale_content_hash(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】原始内容。",
            source_session_id="sid-1",
        )
        item = self.store.list_memories()[0]

        with self.assertRaisesRegex(RuntimeError, "memory_precondition_failed"):
            self.store.update_memory(
                item["path"],
                content="new",
                content_sha256="stale",
            )

    def test_redact_version_scrubs_historical_content_but_not_current(self):
        created = self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】包含 token=secret 的旧内容。",
            source_session_id="sid-1",
        )
        detail = self.store.read_memory(created["path"])
        updated = self.store.update_memory(
            created["path"],
            content=detail["content"] + "\n【核心记忆】新版本。",
            content_sha256=detail["content_sha256"],
            actor="tester",
        )

        redacted = self.store.redact_version(created["version_id"], actor="auditor")
        versions = self.store.list_versions()

        self.assertTrue(redacted["redacted"])
        self.assertEqual(redacted["content"], "[redacted]")
        self.assertEqual(redacted["metadata"]["redacted_by"], "auditor")
        self.assertTrue(any(version.get("redacted") for version in versions))
        with self.assertRaisesRegex(RuntimeError, "memory_version_is_current"):
            self.store.redact_version(updated["version_id"], actor="auditor")

    def test_review_items_and_mark_reviewed_support_stale_memory_workflow(self):
        self.store.append_memory(
            scope_id="sid-1",
            summary="【核心记忆】需要定期复核。",
            source_session_id="sid-1",
        )
        item = self.store.list_memories()[0]
        target = self.tmp_path / item["path"]
        old_time = time.time() - 200 * 24 * 60 * 60
        os.utime(target, (old_time, old_time))

        review_items = self.store.list_review_items(stale_days=180)
        version = self.store.mark_reviewed(item["path"], actor="tester")

        self.assertEqual(len(review_items), 1)
        self.assertGreaterEqual(review_items[0]["age_days"], 199)
        self.assertEqual(version["operation"], "modified")
        self.assertIn("【复核状态】已复核", self.store.read_memory(item["path"])["content"])

    def test_analyze_quality_reports_candidate_only_compression_advice(self):
        for index in range(2):
            self.store.append_memory(
                scope_id="sid-1",
                summary=f"【核心记忆】重复巡检经验 {index}。",
                source_session_id="sid-1",
            )
        for index in range(12):
            self.store.append_memory(
                scope_id="sid-8",
                summary=f"【核心记忆】巡检碎片 {index}。",
                source_session_id="sid-8",
            )

        quality = self.store.analyze_quality(
            pending_conflicts=[{"version_id": "v1"}],
            recent_versions=[],
            max_candidates=5,
        )

        self.assertGreaterEqual(quality["summary"]["memory_count"], 2)
        self.assertGreaterEqual(quality["summary"]["entry_count"], 14)
        self.assertGreaterEqual(quality["summary"]["compression_candidate_count"], 1)
        self.assertEqual(quality["summary"]["pending_conflict_count"], 1)
        self.assertFalse(quality["policy"]["auto_apply"])
        self.assertEqual(quality["policy"]["mode"], "candidate_only")
        self.assertTrue(
            any(candidate["path"].endswith("memory.md") for candidate in quality["compression_candidates"])
        )

    def test_default_memory_stores_only_expose_session_scope(self):
        self.store.initialize()
        exported = self.store.export_store()

        self.assertEqual([store["id"] for store in exported["stores"]], ["sessions"])

    def test_memory_paths_are_scoped_and_sanitized(self):
        self.assertEqual(safe_memory_segment("../evil host"), "evil_host")
        self.assertEqual(
            memory_scope_path("asset-kind:oracle/sql").as_posix(),
            "asset_kinds/oracle_sql/memory.md",
        )


if __name__ == "__main__":
    unittest.main()
