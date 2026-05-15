from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MEMORY_STORES = [
    {
        "id": "sessions",
        "name": "会话记忆",
        "description": "单次会话产生的会话状态、成功经验、错误反馈和审计归档。",
        "path_prefix": "sessions/",
        "access": "read_write",
        "lifecycle": "session_scoped",
        "memory_model": "hermes_style_session_retention",
        "instructions": "Hermes-style：完整会话轨迹留在会话历史用于审计，文件记忆只保存当前 session 的会话状态、成功经验和错误反馈；审计归档可保留但默认不进入提示词。知识库/RAG 可以共享，普通会话记忆不得跨 session 共享。",
    },
]

LEGACY_SHARED_MEMORY_STORE = {
    "id": "legacy_shared",
    "name": "历史共享记忆（只读归档）",
    "description": "旧版本按资产、主机或资产类型沉淀的共享记忆。仅保留用于审计追溯，不再作为新会话上下文自动引用。",
    "path_prefix": "assets/, hosts/, asset_kinds/",
    "access": "read_only",
    "lifecycle": "legacy_archived",
    "instructions": "历史遗留共享记忆只允许读取和导出；新会话只能使用当前 session 记忆，不能继续写入 asset/asset-host/asset-kind 共享范围。",
}

HERMES_MEMORY_MODEL_ID = "hermes_style_session_retention"
LEARNING_CANDIDATE_STATUSES = {"draft", "reviewing", "approved", "rejected", "published"}

MEMORY_KIND_LABELS = {
    "session_state": "会话状态",
    "success_experience": "成功经验",
    "error_feedback": "错误反馈",
    "asset_profile": "资产画像",
    "user_preference": "用户偏好",
    "platform_rule": "平台规则",
    "audit_archive": "审计归档",
    "session_trajectory": "会话轨迹",
}

NON_PROMPT_MEMORY_KINDS = {"audit_archive", "session_trajectory"}


def safe_memory_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    segment = segment.strip("._-")
    return segment[:96] or "default"


def is_legacy_shared_memory_scope(scope_id: str) -> bool:
    scope = str(scope_id or "").strip().lower()
    return scope.startswith(("asset:", "asset-host:", "asset-kind:"))


def memory_scope_path(scope_id: str) -> Path:
    scope = str(scope_id or "").strip().lower()
    if scope.startswith("asset:"):
        return Path("assets") / safe_memory_segment(scope[len("asset:") :]) / "memory.md"
    if scope.startswith("asset-host:"):
        return Path("hosts") / safe_memory_segment(scope[len("asset-host:") :]) / "memory.md"
    if scope.startswith("asset-kind:"):
        return Path("asset_kinds") / safe_memory_segment(scope[len("asset-kind:") :]) / "memory.md"
    return Path("sessions") / safe_memory_segment(scope) / "memory.md"


def memory_content_sha256(content: str) -> str:
    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()


class FileMemoryStore:
    """Claude-style file-backed memory store for long-term OpsCore learnings."""

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)

    def initialize(self) -> None:
        self.root_path.mkdir(parents=True, exist_ok=True)
        (self.root_path / "versions").mkdir(parents=True, exist_ok=True)
        registry_path = self.root_path / "stores.json"
        if not registry_path.exists():
            registry_path.write_text(
                json.dumps(DEFAULT_MEMORY_STORES, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def append_memory(
        self,
        *,
        scope_id: str,
        summary: str,
        source_session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        if is_legacy_shared_memory_scope(scope_id):
            raise ValueError("历史共享记忆已归档，只允许写入当前会话记忆")
        relative_path = memory_scope_path(scope_id)
        target_path = self._resolve_memory_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = dict(metadata or {})
        summary = str(summary or "").strip()
        if not summary:
            raise ValueError("memory summary is empty")
        metadata = self._normalize_entry_metadata(
            summary=summary,
            metadata=metadata,
            timestamp=now,
        )

        existed = target_path.exists()
        old_content = target_path.read_text(encoding="utf-8") if existed else ""
        entry = self._format_entry(
            timestamp=now,
            scope_id=scope_id,
            source_session_id=source_session_id,
            summary=summary,
            metadata=metadata,
        )
        if not old_content:
            new_content = self._initial_header(scope_id) + entry
        else:
            new_content = old_content.rstrip() + "\n\n" + entry
        target_path.write_text(new_content, encoding="utf-8")

        version = {
            "version_id": self._version_id(now, relative_path.as_posix(), "modified" if existed else "created", new_content),
            "timestamp": now,
            "operation": "modified" if existed else "created",
            "path": relative_path.as_posix(),
            "scope_id": scope_id,
            "source_session_id": source_session_id,
            "content_sha256": memory_content_sha256(new_content),
            "summary_sha256": memory_content_sha256(summary),
            "metadata": metadata,
            "content": new_content,
            "previous_content": old_content,
        }
        self._append_version(version)
        return version

    def search(
        self,
        *,
        scope_ids: list[str],
        query: str,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        self.initialize()
        entries: list[dict[str, Any]] = []
        for scope_id in scope_ids:
            path = self._resolve_memory_path(memory_scope_path(scope_id))
            if not path.exists():
                continue
            entries.extend(
                entry
                for entry in self._parse_entries(scope_id, path)
                if entry.get("retrieval_enabled") is not False
            )

        ranked = []
        for entry in entries:
            ranked.append((self._score_entry(entry, query), entry))
        ranked.sort(
            key=lambda item: (
                item[0],
                str(item[1].get("timestamp") or ""),
            ),
            reverse=True,
        )
        results = []
        seen = set()
        for score, entry in ranked:
            key = entry.get("summary_sha256") or memory_content_sha256(entry.get("summary", ""))
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "session_id": entry.get("scope_id"),
                    "_memory_scope_id": entry.get("scope_id"),
                    "timestamp": entry.get("timestamp"),
                    "summary": entry.get("summary"),
                    "memory_model": entry.get("memory_model") or HERMES_MEMORY_MODEL_ID,
                    "memory_kind": entry.get("memory_kind") or "session_state",
                    "memory_kind_label": entry.get("memory_kind_label") or "会话状态",
                    "retention_tier": entry.get("retention_tier") or "session_state",
                    "usage_role": entry.get("usage_role") or "state",
                    "retrieval_enabled": entry.get("retrieval_enabled") is not False,
                    "_distance": 1.0 / max(score, 0.1),
                    "path": entry.get("path"),
                }
            )
            if len(results) >= max(1, limit):
                break
        return results

    def list_memories(self) -> list[dict[str, Any]]:
        self.initialize()
        memories = []
        for path in sorted(self.root_path.rglob("*.md")):
            if "versions" in path.relative_to(self.root_path).parts:
                continue
            content = path.read_text(encoding="utf-8")
            relative_path = path.relative_to(self.root_path).as_posix()
            store = self._store_for_path(relative_path)
            entries = self._parse_entries(self._scope_from_path(relative_path), path)
            is_legacy = self._is_legacy_shared_path(relative_path)
            entry_kinds: dict[str, int] = {}
            retrieval_entries = 0
            audit_entries = 0
            for entry in entries:
                kind = str(entry.get("memory_kind") or "session_state")
                entry_kinds[kind] = entry_kinds.get(kind, 0) + 1
                if entry.get("retrieval_enabled") is False:
                    audit_entries += 1
                else:
                    retrieval_entries += 1
            memories.append(
                {
                    "path": relative_path,
                    "scope_id": self._scope_from_path(relative_path),
                    "store_id": store["id"],
                    "store_name": store["name"],
                    "access": store["access"],
                    "lifecycle": store.get("lifecycle") or "",
                    "memory_model": store.get("memory_model") or HERMES_MEMORY_MODEL_ID,
                    "archived": is_legacy,
                    "legacy": is_legacy,
                    "retrieval_enabled": not is_legacy and retrieval_entries > 0,
                    "retrieval_entries": retrieval_entries,
                    "audit_entries": audit_entries,
                    "entry_kinds": entry_kinds,
                    "usage_policy": store.get("instructions") or "",
                    "size": path.stat().st_size,
                    "entries": len(entries),
                    "updated_at": datetime.datetime.fromtimestamp(
                        path.stat().st_mtime
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "preview": self._preview(content),
                }
            )
        return memories

    def analyze_quality(
        self,
        *,
        stale_days: int = 180,
        pending_conflicts: list[dict[str, Any]] | None = None,
        recent_versions: list[dict[str, Any]] | None = None,
        max_candidates: int = 8,
    ) -> dict[str, Any]:
        self.initialize()
        memories = self.list_memories()
        pending_conflicts = list(pending_conflicts or [])
        recent_versions = recent_versions if recent_versions is not None else self.list_versions(limit=200)
        review_items = self.list_review_items(stale_days=stale_days)
        stale_paths = {item.get("path") for item in review_items}

        by_store: dict[str, dict[str, Any]] = {}
        for item in memories:
            store_id = str(item.get("store_id") or "unknown")
            bucket = by_store.setdefault(
                store_id,
                {
                    "store_id": store_id,
                    "store_name": item.get("store_name") or store_id,
                    "memories": 0,
                    "entries": 0,
                    "size": 0,
                },
            )
            bucket["memories"] += 1
            bucket["entries"] += int(item.get("entries") or 0)
            bucket["size"] += int(item.get("size") or 0)

        version_counts: dict[str, int] = {}
        for version in recent_versions:
            path = str(version.get("path") or "")
            if path:
                version_counts[path] = version_counts.get(path, 0) + 1

        candidates: list[dict[str, Any]] = []
        duplicate_entry_count = 0
        for item in memories:
            path = str(item.get("path") or "")
            reasons: list[str] = []
            score = 0
            entries = int(item.get("entries") or 0)
            size = int(item.get("size") or 0)

            if entries >= 12:
                reasons.append(f"该文件累计 {entries} 条记忆，建议压缩成阶段性结论。")
                score += 30
            if size >= 24000:
                reasons.append(f"文件大小约 {round(size / 1024, 1)} KiB，可能影响检索上下文预算。")
                score += 20
            if path in stale_paths:
                reasons.append(f"超过 {stale_days} 天未复核，需要确认是否仍适用。")
                score += 20
            if version_counts.get(path, 0) >= 5:
                reasons.append(f"最近版本变更 {version_counts[path]} 次，可能存在反复修订或冲突。")
                score += 15

            duplicate_count = 0
            try:
                memory_path = self._resolve_memory_path(self._safe_relative_path(path))
                entry_hashes: dict[str, int] = {}
                for entry in self._parse_entries(str(item.get("scope_id") or ""), memory_path):
                    key = str(entry.get("summary_sha256") or "")
                    if key:
                        entry_hashes[key] = entry_hashes.get(key, 0) + 1
                duplicate_count = sum(count - 1 for count in entry_hashes.values() if count > 1)
            except Exception:
                duplicate_count = 0
            if duplicate_count:
                duplicate_entry_count += duplicate_count
                reasons.append(f"发现 {duplicate_count} 条重复或高度相同的记忆片段。")
                score += 25

            if reasons:
                candidates.append(
                    {
                        "path": path,
                        "scope_id": item.get("scope_id") or "",
                        "store_id": item.get("store_id") or "",
                        "store_name": item.get("store_name") or "",
                        "entries": entries,
                        "size": size,
                        "updated_at": item.get("updated_at") or "",
                        "priority": "high" if score >= 45 else "medium" if score >= 25 else "low",
                        "score": score,
                        "reason": "；".join(reasons),
                        "recommended_action": "先由辅助模型生成压缩草稿，再人工确认后替换原记忆，保留版本记录。",
                    }
                )

        candidates.sort(key=lambda item: (int(item.get("score") or 0), str(item.get("updated_at") or "")), reverse=True)
        candidate_count = len(candidates)
        memory_count = len(memories)
        entry_count = sum(int(item.get("entries") or 0) for item in memories)
        pending_count = len(pending_conflicts)
        stale_count = len(review_items)
        deductions = min(80, pending_count * 10 + stale_count * 6 + candidate_count * 4 + duplicate_entry_count * 3)
        health_score = max(0, 100 - deductions)
        return {
            "summary": {
                "memory_count": memory_count,
                "entry_count": entry_count,
                "store_count": len(by_store),
                "pending_conflict_count": pending_count,
                "stale_review_count": stale_count,
                "compression_candidate_count": candidate_count,
                "duplicate_entry_count": duplicate_entry_count,
                "recent_version_count": len(recent_versions),
                "health_score": health_score,
            },
            "stores": list(by_store.values()),
            "compression_candidates": candidates[: max(1, max_candidates)],
            "policy": {
                "mode": "candidate_only",
                "stale_days": stale_days,
                "auto_apply": False,
                "rule": "只生成压缩候选和治理建议，不自动覆盖正式记忆。",
            },
        }

    def list_review_items(self, *, stale_days: int) -> list[dict[str, Any]]:
        self.initialize()
        if stale_days <= 0:
            return []
        now = datetime.datetime.now()
        review_items = []
        for item in self.list_memories():
            try:
                updated_at = datetime.datetime.strptime(
                    str(item.get("updated_at") or ""),
                    "%Y-%m-%d %H:%M:%S",
                )
            except Exception:
                continue
            age_days = (now - updated_at).days
            if age_days <= stale_days:
                continue
            review_items.append(
                {
                    **item,
                    "age_days": age_days,
                    "stale_days": stale_days,
                    "reason": f"该记忆已 {age_days} 天未复核，超过 {stale_days} 天阈值。",
                    "recommended_action": "结合当前资产状态重新验证，确认仍适用后标记已复核；不再适用则编辑或删除。",
                }
            )
        return review_items

    def list_candidate_entries(
        self,
        *,
        limit: int = 50,
        review_statuses: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.initialize()
        allowed_statuses = {
            str(status).strip()
            for status in (review_statuses or ["pending"])
            if str(status or "").strip()
        }
        if not allowed_statuses:
            allowed_statuses = {"pending"}
        candidates: list[dict[str, Any]] = []
        for path in sorted(self.root_path.rglob("*.md")):
            relative_path = path.relative_to(self.root_path)
            if "versions" in relative_path.parts:
                continue
            if self._is_legacy_shared_path(relative_path.as_posix()):
                continue
            for entry in self._parse_entries(self._scope_from_path(relative_path.as_posix()), path):
                metadata = entry.get("metadata") or {}
                review_status = str(metadata.get("review_status") or "")
                if review_status not in allowed_statuses:
                    continue
                candidates.append(
                    {
                        "candidate_id": self._candidate_id(relative_path.as_posix(), entry),
                        "path": relative_path.as_posix(),
                        "scope_id": entry.get("scope_id") or "",
                        "timestamp": entry.get("timestamp") or "",
                        "source_session_id": entry.get("source_session_id") or "",
                        "summary": entry.get("summary") or "",
                        "summary_preview": self._preview(entry.get("summary") or ""),
                        "memory_kind": entry.get("memory_kind") or "session_state",
                        "memory_kind_label": entry.get("memory_kind_label") or "会话状态",
                        "candidate_type": metadata.get("candidate_type") or "memory_candidate",
                        "review_status": review_status or "pending",
                        "retrieval_enabled": entry.get("retrieval_enabled") is not False,
                        "feedback_target_message_id": metadata.get("feedback_target_message_id"),
                        "source_refs": self._candidate_source_refs(relative_posix=relative_path.as_posix(), entry=entry),
                        "evidence_refs": self._candidate_evidence_refs(metadata),
                        "recommended_action": self._candidate_recommended_action(review_status),
                    }
                )
        candidates.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return candidates[: max(1, min(limit, 200))]

    def _candidate_recommended_action(self, review_status: str) -> str:
        if review_status == "runbook_candidate":
            return "等待人工整理成 Runbook，再发布到可复用运维流程；当前不进入模型检索上下文。"
        if review_status == "skill_candidate":
            return "等待人工整理成 Skill，并通过校验后再进入技能体系；当前不进入模型检索上下文。"
        return "人工确认后再允许进入当前会话长期记忆检索上下文。"

    def list_learning_candidates(self, *, limit: int = 50, target_type: str = "") -> list[dict[str, Any]]:
        self.initialize()
        allowed_target = str(target_type or "").strip()
        items: list[dict[str, Any]] = []
        pool_path = self._learning_candidate_pool_path()
        if not pool_path.exists():
            return []
        for line in pool_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            if allowed_target and item.get("target_type") != allowed_target:
                continue
            items.append(item)
        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return items[: max(1, min(limit, 200))]

    def update_learning_candidate_status(
        self,
        candidate_id: str,
        *,
        status: str,
        actor: str = "user",
        reason: str = "",
    ) -> dict[str, Any]:
        self.initialize()
        normalized_id = str(candidate_id or "").strip()
        normalized_status = str(status or "").strip().lower()
        normalized_actor = str(actor or "user").strip() or "user"
        normalized_reason = str(reason or "").strip()
        if not normalized_id:
            raise ValueError("发布候选 ID 不能为空")
        if normalized_status not in LEARNING_CANDIDATE_STATUSES:
            raise ValueError("发布候选状态无效")
        if not normalized_reason:
            raise ValueError("状态变更理由不能为空")

        pool_path = self._learning_candidate_pool_path()
        if not pool_path.exists():
            raise FileNotFoundError(normalized_id)
        rows = self._read_learning_candidate_rows()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changed = False
        for item in rows:
            if str(item.get("id") or "") != normalized_id:
                continue
            previous_status = str(item.get("status") or "draft")
            if normalized_status in {"approved", "published"} and not self._learning_candidate_quality_ready(item):
                raise ValueError("发布候选质量清单未全部通过，不能批准或发布")
            item["status"] = normalized_status
            item["updated_at"] = now
            events = item.get("status_events")
            if not isinstance(events, list):
                events = []
            events.append(
                {
                    "from": previous_status,
                    "to": normalized_status,
                    "actor": normalized_actor,
                    "reason": normalized_reason,
                    "timestamp": now,
                }
            )
            item["status_events"] = events
            if normalized_status == "published":
                item["published_artifact"] = self._generate_learning_candidate_publish_artifact(
                    item=item,
                    actor=normalized_actor,
                    reason=normalized_reason,
                    now=now,
                )
            changed = True
            updated = item
            break
        else:
            raise FileNotFoundError(normalized_id)
        if not changed:
            raise FileNotFoundError(normalized_id)
        self._write_learning_candidate_rows(rows)
        return updated

    def read_learning_candidate_publish_artifact(self, candidate_id: str) -> dict[str, Any]:
        self.initialize()
        normalized_id = str(candidate_id or "").strip()
        if not normalized_id:
            raise ValueError("发布候选 ID 不能为空")

        for item in self._read_learning_candidate_rows():
            if str(item.get("id") or "") != normalized_id:
                continue
            artifact = item.get("published_artifact")
            if not isinstance(artifact, dict):
                raise FileNotFoundError(normalized_id)

            file_path = str(artifact.get("file_path") or "").strip()
            if not file_path:
                raise FileNotFoundError(normalized_id)
            try:
                artifact_path = self.resolve_learning_candidate_publish_artifact_path(file_path)
            except ValueError as exc:
                raise FileNotFoundError(normalized_id) from exc

            if not artifact_path.exists():
                raise FileNotFoundError(normalized_id)

            content = artifact_path.read_text(encoding="utf-8")
            return {
                "candidate_id": item.get("id", ""),
                "artifact_id": str(artifact.get("artifact_id") or ""),
                "target_type": str(artifact.get("target_type") or item.get("target_type", "")),
                "file_path": file_path,
                "status": str(artifact.get("status") or "draft"),
                "generated_by": str(artifact.get("generated_by") or ""),
                "generated_reason": str(artifact.get("generated_reason") or ""),
                "generated_at": str(artifact.get("generated_at") or ""),
                "content_preview": str(artifact.get("content_preview") or ""),
                "artifact_sha256": str(artifact.get("artifact_sha256") or ""),
                "content_sha256": str(artifact.get("content_sha256") or ""),
                "artifact_size": artifact.get("artifact_size", 0),
                "content": content,
            }
        raise FileNotFoundError(normalized_id)

    def resolve_learning_candidate_publish_artifact_path(self, file_path: str) -> Path:
        if not str(file_path or "").strip():
            raise ValueError("artifact file_path is required")
        return self._resolve_memory_path(self._safe_relative_path(file_path))

    def _learning_candidate_quality_ready(self, item: dict[str, Any]) -> bool:
        checklist = item.get("quality_checklist")
        if not isinstance(checklist, list) or not checklist:
            return False
        return all(isinstance(row, dict) and row.get("ok") is True for row in checklist)

    def _generate_learning_candidate_publish_artifact(
        self,
        *,
        item: dict[str, Any],
        actor: str,
        reason: str,
        now: str,
    ) -> dict[str, Any]:
        target_type = str(item.get("target_type") or "runbook").strip() or "runbook"
        existing = item.get("published_artifact")
        if isinstance(existing, dict):
            artifact_id = str(existing.get("artifact_id") or "").strip()
        else:
            artifact_id = ""
        if not artifact_id:
            artifact_id = f"publish_{memory_content_sha256(str(item.get('id') or '') + '|' + target_type)[:18]}"
        artifact_id = safe_memory_segment(artifact_id) if artifact_id else safe_memory_segment(f"publish_{item.get('id', 'candidate')}")
        if not artifact_id.startswith("publish_"):
            artifact_id = f"publish_{artifact_id}"

        artifact_path = self._learning_candidate_publish_artifact_path(
            artifact_id=artifact_id,
            target_type=target_type,
        )
        artifact_content = self._render_learning_candidate_publish_artifact(
            item=item,
            artifact_id=artifact_id,
            target_type=target_type,
            actor=actor,
            reason=reason,
            now=now,
        )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(artifact_content, encoding="utf-8")
        return {
            "artifact_id": artifact_id,
            "target_type": target_type,
            "file_path": artifact_path.relative_to(self.root_path).as_posix(),
            "status": "draft",
            "generated_by": actor,
            "generated_reason": reason,
            "generated_at": now,
            "content_sha256": memory_content_sha256(artifact_content),
            "artifact_sha256": memory_content_sha256(artifact_content),
            "artifact_size": len(artifact_content.encode("utf-8")),
            "content_preview": self._preview(artifact_content),
        }

    def _render_learning_candidate_publish_artifact(
        self,
        *,
        item: dict[str, Any],
        artifact_id: str,
        target_type: str,
        actor: str,
        reason: str,
        now: str,
    ) -> str:
        label = "Runbook" if target_type == "runbook" else "Skill"
        summary = str(item.get("summary") or "").strip() or "无摘要"
        source_session = str(item.get("source_session_id") or "").strip()
        target = str(item.get("source_path") or "").strip()
        checklist = item.get("quality_checklist")
        if not isinstance(checklist, list):
            checklist = []
        evidence_count = len(item.get("evidence_refs") or [])
        lines = [
            f"# {label} 发布草稿",
            "",
            f"- artifact_id: {artifact_id}",
            f"- candidate_id: {item.get('id', '')}",
            f"- target_type: {target_type}",
            f"- source_candidate_id: {item.get('source_candidate_id', '')}",
            f"- source_session_id: {source_session or '-'}",
            f"- source_path: {target or '-'}",
            f"- generated_by: {actor}",
            f"- generated_at: {now}",
            f"- generated_reason: {reason}",
            "",
            "## 来源摘要",
            self._preview(summary),
            "",
            "## 质量清单（发布前）",
        ]
        if checklist:
            for row in checklist:
                key = str(row.get("key") or "").strip()
                label_row = str(row.get("label") or key or "检查项")
                ok = bool(row.get("ok"))
                note = str(row.get("note") or "").strip()
                lines.append(f"- [{'x' if ok else ' '}] {label_row}")
                if note:
                    lines.append(f"  - 说明：{note}")
        else:
            lines.append("- 尚未生成清单")
        lines.extend([
            "",
            f"## 证据与引用",
            f"- evidence_refs: {evidence_count}",
            "",
            "## 草稿说明",
            "- 已通过运行时质量门禁并标记为已发布。",
            "- 上线前请补齐审批与灰度计划；仅用于人工审核与运行时接入。",
            "",
        ])
        return "\n".join(lines).rstrip() + "\n"

    def _learning_candidate_publish_artifact_path(self, *, artifact_id: str, target_type: str) -> Path:
        safe_target_type = safe_memory_segment(target_type or "runbook")
        return (
            self.root_path
            / "learning_candidate_publish_artifacts"
            / safe_target_type
            / f"{artifact_id}.md"
        )

    def update_learning_candidate_quality_checklist(
        self,
        candidate_id: str,
        *,
        checklist: list[dict[str, Any]],
        actor: str = "user",
        reason: str = "",
    ) -> dict[str, Any]:
        self.initialize()
        normalized_id = str(candidate_id or "").strip()
        normalized_actor = str(actor or "user").strip() or "user"
        normalized_reason = str(reason or "").strip()
        normalized_checklist = self._normalize_learning_candidate_quality_checklist(checklist)
        if not normalized_id:
            raise ValueError("发布候选 ID 不能为空")
        if not normalized_checklist:
            raise ValueError("发布质量清单不能为空")
        if not normalized_reason:
            raise ValueError("质量清单变更理由不能为空")

        pool_path = self._learning_candidate_pool_path()
        if not pool_path.exists():
            raise FileNotFoundError(normalized_id)
        rows = self._read_learning_candidate_rows()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in rows:
            if str(item.get("id") or "") != normalized_id:
                continue
            item["quality_checklist"] = normalized_checklist
            item["updated_at"] = now
            events = item.get("quality_events")
            if not isinstance(events, list):
                events = []
            events.append(
                {
                    "actor": normalized_actor,
                    "reason": normalized_reason,
                    "timestamp": now,
                    "passed": sum(1 for row in normalized_checklist if row.get("ok") is True),
                    "total": len(normalized_checklist),
                }
            )
            item["quality_events"] = events
            self._write_learning_candidate_rows(rows)
            return item
        raise FileNotFoundError(normalized_id)

    def _read_learning_candidate_rows(self) -> list[dict[str, Any]]:
        pool_path = self._learning_candidate_pool_path()
        if not pool_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in pool_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                rows.append(item)
        return rows

    def _write_learning_candidate_rows(self, rows: list[dict[str, Any]]) -> None:
        pool_path = self._learning_candidate_pool_path()
        pool_path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        pool_path.write_text((payload + "\n") if payload else "", encoding="utf-8")

    def _learning_candidate_pool_path(self) -> Path:
        return self.root_path / "learning_candidates.jsonl"

    def _append_learning_candidate(
        self,
        *,
        source_candidate_id: str,
        target_type: str,
        source_path: str,
        entry: dict[str, Any],
        actor: str,
    ) -> dict[str, Any]:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = entry.get("metadata") or {}
        payload_seed = "|".join(
            [
                source_candidate_id,
                target_type,
                source_path,
                str(entry.get("summary") or ""),
            ]
        )
        item = {
            "id": f"learncand_{memory_content_sha256(payload_seed)[:18]}",
            "target_type": target_type,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "actor": actor,
            "source_candidate_id": source_candidate_id,
            "source_path": source_path,
            "source_session_id": entry.get("source_session_id") or "",
            "feedback_target_message_id": metadata.get("feedback_target_message_id"),
            "summary": entry.get("summary") or "",
            "summary_preview": self._preview(entry.get("summary") or ""),
            "memory_kind": entry.get("memory_kind") or "success_experience",
            "source_refs": self._candidate_source_refs(relative_posix=source_path, entry=entry),
            "evidence_refs": self._candidate_evidence_refs(metadata),
            "next_action": (
                "整理成 Runbook 草稿，补齐适用范围、前置条件、步骤、回滚和验证。"
                if target_type == "runbook"
                else "整理成 Skill 草稿，补齐输入、脚本、权限边界、测试和回滚。"
            ),
            "quality_checklist": self._learning_candidate_quality_checklist(
                target_type=target_type,
                entry=entry,
                metadata=metadata,
            ),
            "status_events": [
                {
                    "from": "",
                    "to": "draft",
                    "actor": actor,
                    "reason": "由学习候选转换生成发布候选。",
                    "timestamp": now,
                }
            ],
        }
        pool_path = self._learning_candidate_pool_path()
        pool_path.parent.mkdir(parents=True, exist_ok=True)
        existing_ids = {str(row.get("id")) for row in self.list_learning_candidates(limit=200)}
        if item["id"] not in existing_ids:
            with pool_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        return item

    def _learning_candidate_quality_checklist(
        self,
        *,
        target_type: str,
        entry: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        has_source = bool(entry.get("source_session_id"))
        has_feedback = bool(metadata.get("feedback_target_message_id"))
        has_evidence = bool(self._candidate_evidence_refs(metadata))
        common = [
            {"key": "source_message", "label": "来源消息", "ok": has_source and has_feedback},
            {"key": "tool_evidence", "label": "工具证据", "ok": has_evidence},
            {"key": "scope", "label": "适用范围", "ok": False},
            {"key": "risk_boundary", "label": "风险边界", "ok": False},
            {"key": "rollback", "label": "回滚方案", "ok": False},
        ]
        if target_type == "runbook":
            common.insert(3, {"key": "steps", "label": "执行步骤", "ok": False})
            common.append({"key": "verification", "label": "验证项", "ok": False})
        else:
            common.insert(3, {"key": "inputs", "label": "输入参数", "ok": False})
            common.append({"key": "tests", "label": "测试项", "ok": False})
        return common

    def _normalize_learning_candidate_quality_checklist(self, checklist: Any) -> list[dict[str, Any]]:
        if not isinstance(checklist, list):
            return []
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in checklist:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            label = str(raw.get("label") or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            item: dict[str, Any] = {
                "key": key[:80],
                "label": (label or key)[:120],
                "ok": bool(raw.get("ok")),
            }
            note = str(raw.get("note") or raw.get("detail") or "").strip()
            if note:
                item["note"] = note[:500]
            normalized.append(item)
        return normalized[:20]

    def _candidate_source_refs(self, *, relative_posix: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = entry.get("metadata") or {}
        refs = self._normalize_ref_list(metadata.get("source_refs"))
        source_session_id = str(entry.get("source_session_id") or "").strip()
        if source_session_id:
            refs.append({"type": "session", "label": "来源会话", "id": source_session_id})
        feedback_message_id = metadata.get("feedback_target_message_id")
        if feedback_message_id is not None and str(feedback_message_id).strip():
            refs.append({"type": "message", "label": "反馈消息", "id": str(feedback_message_id)})
        refs.append({"type": "memory_file", "label": "记忆文件", "path": relative_posix})
        return self._dedupe_refs(refs)[:8]

    def _candidate_evidence_refs(self, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        refs = self._normalize_ref_list(metadata.get("evidence_refs"))
        for evidence_id in self._normalize_string_list(metadata.get("evidence_ids")):
            refs.append({"type": "tool_evidence", "label": "工具证据", "id": evidence_id})
        for tool_call_id in self._normalize_string_list(metadata.get("tool_call_ids")):
            refs.append({"type": "tool_call", "label": "工具调用", "id": tool_call_id})
        return self._dedupe_refs(refs)[:12]

    def _normalize_ref_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        refs: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                compact = {str(key): val for key, val in item.items() if val not in (None, "")}
                if compact:
                    refs.append(compact)
            elif str(item or "").strip():
                refs.append({"id": str(item).strip()})
        return refs

    def _normalize_string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item or "").strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _dedupe_refs(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ref in refs:
            key = "|".join(
                [
                    str(ref.get("type") or ""),
                    str(ref.get("id") or ""),
                    str(ref.get("path") or ""),
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ref)
        return deduped

    def resolve_candidate_entry(self, candidate_id: str, action: str, *, actor: str = "user") -> dict[str, Any]:
        self.initialize()
        normalized_action = str(action or "").strip().lower()
        if normalized_action not in {"confirm", "reject", "to_runbook", "to_skill"}:
            raise ValueError("候选记忆处理动作无效")
        normalized_id = str(candidate_id or "").strip()
        if not normalized_id:
            raise ValueError("候选记忆 ID 不能为空")

        for path in sorted(self.root_path.rglob("*.md")):
            relative_path = path.relative_to(self.root_path)
            relative_posix = relative_path.as_posix()
            if "versions" in relative_path.parts or self._is_legacy_shared_path(relative_posix):
                continue
            content = path.read_text(encoding="utf-8")
            chunks = re.split(r"(?m)^##\s+", content)
            if len(chunks) <= 1:
                continue
            changed = False
            matched_entry: dict[str, Any] | None = None
            rewritten = [chunks[0]]
            for chunk in chunks[1:]:
                entry = self._parse_entry_chunk(
                    self._scope_from_path(relative_posix),
                    relative_posix,
                    chunk,
                )
                if (
                    entry
                    and self._candidate_id(relative_posix, entry) == normalized_id
                    and (entry.get("metadata") or {}).get("review_status") == "pending"
                ):
                    rewritten.append(self._rewrite_candidate_chunk(chunk, normalized_action))
                    matched_entry = entry
                    changed = True
                else:
                    rewritten.append(f"## {chunk}")
            if not changed:
                continue
            new_content = "".join(rewritten)
            version = self.update_memory(
                relative_posix,
                content=new_content,
                content_sha256=memory_content_sha256(content),
                actor=f"memory_candidate:{normalized_action}:{actor}",
            )
            if normalized_action in {"to_runbook", "to_skill"} and matched_entry:
                learning_candidate = self._append_learning_candidate(
                    source_candidate_id=normalized_id,
                    target_type="runbook" if normalized_action == "to_runbook" else "skill",
                    source_path=relative_posix,
                    entry=matched_entry,
                    actor=actor,
                )
                version["learning_candidate"] = learning_candidate
            return version
        raise FileNotFoundError(normalized_id)

    def mark_reviewed(self, path: str, *, actor: str = "user") -> dict[str, Any]:
        detail = self.read_memory(path)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = self._promote_pending_review_entries(str(detail.get("content") or ""))
        review_entry = (
            f"\n\n## {now}\n"
            f"- scope_id: {detail.get('scope_id') or 'global'}\n"
            f"- source_session_id: memory_review:{actor}\n"
            '- metadata: {"source": "memory_review", "review_status": "confirmed"}\n\n'
            "【记忆类型】复核记录\n"
            "【复核状态】已复核\n"
            "【核心记忆】人工确认该记忆文件仍可作为历史经验保留。\n"
            "【使用提醒】后续使用前仍需结合当前资产实时工具结果验证。\n"
        )
        return self.update_memory(
            path,
            content=content.rstrip() + review_entry,
            content_sha256=str(detail.get("content_sha256") or ""),
            actor=f"memory_review:{actor}",
        )

    def _promote_pending_review_entries(self, content: str) -> str:
        lines: list[str] = []
        for line in str(content or "").splitlines():
            if line.startswith("- metadata:") and '"review_status": "pending"' in line:
                line = re.sub(
                    r'("review_status"\s*:\s*)"pending"',
                    r'\1"confirmed"',
                    line,
                )
                line = re.sub(
                    r'("retrieval_enabled"\s*:\s*)false',
                    r'\1true',
                    line,
                )
            lines.append(line)
        promoted = "\n".join(lines)
        promoted = promoted.replace("【候选状态】待人工确认", "【候选状态】已人工确认")
        promoted = promoted.replace(
            "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
            "【保留方式】成功经验：已人工确认，可在当前会话后续轮次复用，但使用前必须结合实时工具结果验证。",
        )
        promoted = promoted.replace(
            "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。",
            "【使用提醒】后续使用前仍需结合当前资产实时工具结果验证。",
        )
        return promoted

    def _rewrite_candidate_chunk(self, chunk: str, action: str) -> str:
        status_by_action = {
            "confirm": "confirmed",
            "reject": "rejected",
            "to_runbook": "runbook_candidate",
            "to_skill": "skill_candidate",
        }
        type_by_action = {
            "to_runbook": "runbook_candidate",
            "to_skill": "skill_candidate",
        }
        lines = chunk.splitlines()
        rewritten: list[str] = []
        for line in lines:
            if line.startswith("- metadata:") and '"review_status": "pending"' in line:
                line = re.sub(
                    r'("review_status"\s*:\s*)"pending"',
                    rf'\1"{status_by_action[action]}"',
                    line,
                )
                if action == "confirm":
                    line = re.sub(r'("retrieval_enabled"\s*:\s*)false', r'\1true', line)
                else:
                    line = re.sub(r'("retrieval_enabled"\s*:\s*)true', r'\1false', line)
                if action in type_by_action:
                    if '"candidate_type"' in line:
                        line = re.sub(
                            r'("candidate_type"\s*:\s*)"[^"]*"',
                            rf'\1"{type_by_action[action]}"',
                            line,
                        )
                    else:
                        line = line.rstrip()
                        line = re.sub(r"\}\s*$", f', "candidate_type": "{type_by_action[action]}"}}', line)
            rewritten.append(line)
        updated = "\n".join(rewritten)
        if action == "confirm":
            updated = self._promote_pending_review_entries(updated)
        elif action == "reject":
            updated = updated.replace("【候选状态】待人工确认", "【候选状态】已拒绝")
            updated = updated.replace(
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
                "【保留方式】已拒绝候选：仅用于审计，不进入模型检索上下文。",
            )
            updated = updated.replace(
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。",
                "【使用提醒】该候选已被拒绝，不得作为事实、建议或成功经验沉淀。",
            )
        elif action == "to_runbook":
            updated = updated.replace("【候选状态】待人工确认", "【候选状态】已转 Runbook 候选")
            updated = updated.replace(
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
                "【保留方式】Runbook 候选：等待人工整理成可复用运维流程，不进入模型检索上下文。",
            )
            updated = updated.replace(
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。",
                "【使用提醒】该候选尚未发布为 Runbook，不得直接作为执行依据。",
            )
        elif action == "to_skill":
            updated = updated.replace("【候选状态】待人工确认", "【候选状态】已转 Skill 候选")
            updated = updated.replace(
                "【保留方式】候选成功经验：确认前仅用于审计和学习中心展示，不进入模型检索上下文。",
                "【保留方式】Skill 候选：等待人工实现、测试和发布，不进入模型检索上下文。",
            )
            updated = updated.replace(
                "【使用提醒】人工确认后才可作为当前会话后续参考；使用前仍需结合当前资产实时工具结果验证。",
                "【使用提醒】该候选尚未发布为 Skill，不得直接作为自动化能力使用。",
            )
        return f"## {updated.rstrip()}\n"

    def list_stores(self) -> list[dict[str, Any]]:
        self.initialize()
        stores = [
            store
            for store in self._load_store_registry()
            if not self._store_is_legacy_shared(store)
        ]
        if self._has_legacy_shared_memory_files():
            stores.append(dict(LEGACY_SHARED_MEMORY_STORE))
        return stores if stores else list(DEFAULT_MEMORY_STORES)

    def read_memory(self, path: str) -> dict[str, Any]:
        self.initialize()
        relative_path = self._safe_relative_path(path)
        target = self._resolve_memory_path(relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path)
        content = target.read_text(encoding="utf-8")
        entries = self._parse_entries(self._scope_from_path(relative_path.as_posix()), target)
        entry_kinds: dict[str, int] = {}
        retrieval_entries = 0
        audit_entries = 0
        for entry in entries:
            kind = str(entry.get("memory_kind") or "session_state")
            entry_kinds[kind] = entry_kinds.get(kind, 0) + 1
            if entry.get("retrieval_enabled") is False:
                audit_entries += 1
            else:
                retrieval_entries += 1
        return {
            "path": relative_path.as_posix(),
            "scope_id": self._scope_from_path(relative_path.as_posix()),
            "store_id": self._store_for_path(relative_path.as_posix())["id"],
            "store_name": self._store_for_path(relative_path.as_posix())["name"],
            "access": self._store_for_path(relative_path.as_posix())["access"],
            "lifecycle": self._store_for_path(relative_path.as_posix()).get("lifecycle") or "",
            "memory_model": self._store_for_path(relative_path.as_posix()).get("memory_model") or HERMES_MEMORY_MODEL_ID,
            "archived": self._is_legacy_shared_path(relative_path.as_posix()),
            "legacy": self._is_legacy_shared_path(relative_path.as_posix()),
            "retrieval_enabled": not self._is_legacy_shared_path(relative_path.as_posix()) and retrieval_entries > 0,
            "retrieval_entries": retrieval_entries,
            "audit_entries": audit_entries,
            "entry_kinds": entry_kinds,
            "usage_policy": self._store_for_path(relative_path.as_posix()).get("instructions") or "",
            "content": content,
            "content_sha256": memory_content_sha256(content),
            "size": target.stat().st_size,
            "updated_at": datetime.datetime.fromtimestamp(target.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

    def update_memory(
        self,
        path: str,
        *,
        content: str,
        content_sha256: str | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        self.initialize()
        relative_path = self._safe_relative_path(path)
        store = self._store_for_path(relative_path.as_posix())
        if store.get("access") == "read_only":
            raise PermissionError("memory store is read-only")
        target = self._resolve_memory_path(relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path)
        previous_content = target.read_text(encoding="utf-8")
        previous_sha = memory_content_sha256(previous_content)
        if content_sha256 and content_sha256 != previous_sha:
            raise RuntimeError("memory_precondition_failed")
        new_content = str(content or "")
        target.write_text(new_content, encoding="utf-8")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version = {
            "version_id": self._version_id(now, relative_path.as_posix(), "modified", new_content),
            "timestamp": now,
            "operation": "modified",
            "path": relative_path.as_posix(),
            "scope_id": self._scope_from_path(relative_path.as_posix()),
            "source_session_id": actor,
            "content_sha256": memory_content_sha256(new_content),
            "summary_sha256": "",
            "metadata": {"actor": actor},
            "content": new_content,
            "previous_content": previous_content,
        }
        self._append_version(version)
        return version

    def delete_memory(self, path: str, *, actor: str = "user") -> dict[str, Any]:
        self.initialize()
        relative_path = self._safe_relative_path(path)
        store = self._store_for_path(relative_path.as_posix())
        if store.get("access") == "read_only":
            raise PermissionError("memory_store_read_only")
        target = self._resolve_memory_path(relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path)
        content = target.read_text(encoding="utf-8")
        target.unlink()
        version = {
            "version_id": self._version_id(datetime.datetime.now().isoformat(), relative_path.as_posix(), "deleted", content),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operation": "deleted",
            "path": relative_path.as_posix(),
            "scope_id": self._scope_from_path(relative_path.as_posix()),
            "source_session_id": actor,
            "content_sha256": memory_content_sha256(content),
            "summary_sha256": "",
            "metadata": {"actor": actor},
            "content": content,
            "previous_content": content,
        }
        self._append_version(version)
        return version

    def list_versions(self, limit: int = 50) -> list[dict[str, Any]]:
        self.initialize()
        events: list[dict[str, Any]] = []
        for path in sorted((self.root_path / "versions").glob("*.jsonl"), reverse=True):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        events.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return events[: max(1, min(limit, 200))]

    def restore_version(self, version_id: str, *, actor: str = "user") -> dict[str, Any]:
        self.initialize()
        target_version = None
        for version in self.list_versions(limit=200):
            if version.get("version_id") == version_id:
                target_version = version
                break
        if not target_version:
            raise FileNotFoundError(version_id)
        content = target_version.get("content") or target_version.get("previous_content")
        if content is None:
            raise ValueError("version content is unavailable")
        path = str(target_version.get("path") or "")
        relative_path = self._safe_relative_path(path)
        store = self._store_for_path(relative_path.as_posix())
        if store.get("access") == "read_only":
            raise PermissionError("memory store is read-only")
        target = self._resolve_memory_path(relative_path)
        previous_content = target.read_text(encoding="utf-8") if target.exists() else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version = {
            "version_id": self._version_id(now, relative_path.as_posix(), "restored", str(content)),
            "timestamp": now,
            "operation": "restored",
            "path": relative_path.as_posix(),
            "scope_id": self._scope_from_path(relative_path.as_posix()),
            "source_session_id": actor,
            "content_sha256": memory_content_sha256(str(content)),
            "summary_sha256": "",
            "metadata": {"actor": actor, "restored_from": version_id},
            "content": str(content),
            "previous_content": previous_content,
        }
        self._append_version(version)
        return version

    def redact_version(self, version_id: str, *, actor: str = "user") -> dict[str, Any]:
        self.initialize()
        version_path = None
        target_index = -1
        target_version = None
        for path in sorted((self.root_path / "versions").glob("*.jsonl"), reverse=True):
            events = []
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    events.append(None)
            for index, version in enumerate(events):
                if isinstance(version, dict) and version.get("version_id") == version_id:
                    version_path = path
                    target_index = index
                    target_version = version
                    break
            if target_version:
                break
        if not version_path or target_index < 0 or not target_version:
            raise FileNotFoundError(version_id)
        if target_version.get("redacted"):
            return target_version

        relative_path = self._safe_relative_path(str(target_version.get("path") or ""))
        target = self._resolve_memory_path(relative_path)
        if target.exists() and target.is_file():
            current_content = target.read_text(encoding="utf-8")
            if target_version.get("content_sha256") == memory_content_sha256(current_content):
                raise RuntimeError("memory_version_is_current")

        redacted = dict(target_version)
        metadata = dict(redacted.get("metadata") or {})
        metadata.update(
            {
                "redacted_by": actor,
                "redacted_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "redaction_reason": "manual_memory_version_redaction",
            }
        )
        redacted["redacted"] = True
        redacted["metadata"] = metadata
        redacted["content"] = "[redacted]"
        redacted["previous_content"] = "[redacted]"
        redacted["content_sha256"] = memory_content_sha256("[redacted]")
        redacted["summary_sha256"] = ""

        rewritten = []
        for index, line in enumerate(version_path.read_text(encoding="utf-8").splitlines()):
            rewritten.append(
                json.dumps(redacted, ensure_ascii=False, sort_keys=True)
                if index == target_index
                else line
            )
        version_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        return redacted

    def export_store(self) -> dict[str, Any]:
        self.initialize()
        memories = []
        for item in self.list_memories():
            detail = self.read_memory(item["path"])
            memories.append(detail)
        return {
            "exported_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stores": self.list_stores(),
            "memories": memories,
            "versions": self.list_versions(limit=200),
        }

    def _resolve_memory_path(self, relative_path: Path) -> Path:
        target = (self.root_path / relative_path).resolve()
        root = self.root_path.resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("memory path escapes store root") from exc
        return target

    def _safe_relative_path(self, value: str) -> Path:
        raw = str(value or "").replace("\\", "/").strip().lstrip("/")
        if not raw or raw.startswith("../") or "/../" in raw or raw == "..":
            raise ValueError("invalid memory path")
        path = Path(raw)
        if path.is_absolute() or path.suffix.lower() != ".md":
            raise ValueError("invalid memory path")
        return path

    def _load_store_registry(self) -> list[dict[str, Any]]:
        registry_path = self.root_path / "stores.json"
        try:
            stores = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            stores = DEFAULT_MEMORY_STORES
        return stores if isinstance(stores, list) else DEFAULT_MEMORY_STORES

    def _store_for_path(self, relative_path: str) -> dict[str, Any]:
        normalized = str(relative_path or "").replace("\\", "/").lstrip("/")
        if self._is_legacy_shared_path(normalized):
            return dict(LEGACY_SHARED_MEMORY_STORE)
        stores = self._load_store_registry()
        for store in stores:
            if self._store_is_legacy_shared(store):
                continue
            prefix = str(store.get("path_prefix") or "").lstrip("/")
            if prefix and normalized.startswith(prefix):
                return store
        active_stores = [store for store in stores if not self._store_is_legacy_shared(store)]
        return active_stores[0] if active_stores else DEFAULT_MEMORY_STORES[0]

    def _is_legacy_shared_path(self, relative_path: str | Path) -> bool:
        parts = Path(str(relative_path or "").replace("\\", "/")).parts
        return bool(parts) and parts[0] in {"assets", "hosts", "asset_kinds"}

    def _store_is_legacy_shared(self, store: dict[str, Any]) -> bool:
        prefix = str(store.get("path_prefix") or "").replace("\\", "/").lstrip("/")
        store_id = str(store.get("id") or "")
        return (
            store_id in {"assets", "hosts", "asset_kinds", "legacy_shared"}
            or prefix.startswith(("assets/", "hosts/", "asset_kinds/"))
        )

    def _has_legacy_shared_memory_files(self) -> bool:
        for folder in ("assets", "hosts", "asset_kinds"):
            if any((self.root_path / folder).glob("**/*.md")):
                return True
        return False

    def _version_id(self, timestamp: str, path: str, operation: str, content: str) -> str:
        digest = memory_content_sha256(f"{timestamp}\n{path}\n{operation}\n{content}")[:16]
        return f"memver_{digest}"

    def _initial_header(self, scope_id: str) -> str:
        return (
            "# OpsCore Memory Store\n\n"
            f"- scope_id: {scope_id}\n"
            "- access: read_write\n"
            f"- memory_model: {HERMES_MEMORY_MODEL_ID}\n"
            "- rule: session-scoped memory only; trajectory/history is retained for audit, prompt context uses compact state/experience/feedback only\n\n"
        )

    def _format_entry(
        self,
        *,
        timestamp: str,
        scope_id: str,
        source_session_id: str,
        summary: str,
        metadata: dict[str, Any],
    ) -> str:
        metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        return (
            f"## {timestamp}\n"
            f"- scope_id: {scope_id}\n"
            f"- source_session_id: {source_session_id}\n"
            f"- metadata: {metadata_json}\n\n"
            f"{summary}\n"
        )

    def _normalize_entry_metadata(
        self,
        *,
        summary: str,
        metadata: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        normalized = dict(metadata or {})
        policy = self._classify_entry(summary, normalized)
        for key, value in policy.items():
            normalized.setdefault(key, value)
        normalized.setdefault("memory_model", HERMES_MEMORY_MODEL_ID)
        normalized.setdefault("created_at", timestamp)
        normalized.setdefault("scope_policy", "current_session_only")
        return normalized

    def _classify_entry(self, summary: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = dict(metadata or {})
        text = str(summary or "")
        source = str(metadata.get("source") or "").strip().lower()
        explicit_kind = str(metadata.get("memory_kind") or "").strip().lower()
        kind = explicit_kind if explicit_kind in MEMORY_KIND_LABELS else ""
        if not kind:
            if source in {"memory_review", "manual_memory_version_redaction"} or "【复核状态】" in text or "复核记录" in text:
                kind = "audit_archive"
            elif "【记忆类型】资产画像" in text:
                kind = "asset_profile"
            elif "用户点踩" in text or "用户纠错反馈" in text or "纠错经验" in text or "错误反馈" in text:
                kind = "error_feedback"
            elif "用户点赞" in text or "用户认可回答" in text or "成功执行经验" in text or "成功经验" in text:
                kind = "success_experience"
            elif "用户偏好" in text:
                kind = "user_preference"
            elif "平台规则" in text:
                kind = "platform_rule"
            elif "会话轨迹" in text or source in {"session_trajectory", "trace_archive"}:
                kind = "session_trajectory"
            else:
                kind = "session_state"

        if kind in NON_PROMPT_MEMORY_KINDS:
            retention_tier = "audit_archive"
            usage_role = "audit_only"
            retrieval_enabled = False
        elif kind == "error_feedback":
            retention_tier = "negative_learning"
            usage_role = "avoidance"
            retrieval_enabled = True
        elif kind == "success_experience":
            retention_tier = "success_experience"
            usage_role = "reuse_after_live_verification"
            retrieval_enabled = True
        elif kind == "asset_profile":
            retention_tier = "session_state"
            usage_role = "profile_prompt"
            retrieval_enabled = True
        else:
            retention_tier = "session_state"
            usage_role = "state"
            retrieval_enabled = True

        return {
            "memory_model": HERMES_MEMORY_MODEL_ID,
            "memory_kind": kind,
            "memory_kind_label": MEMORY_KIND_LABELS.get(kind, "会话状态"),
            "retention_tier": retention_tier,
            "usage_role": usage_role,
            "retrieval_enabled": retrieval_enabled,
        }

    def _append_version(self, version: dict[str, Any]) -> None:
        version_path = (
            self.root_path
            / "versions"
            / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.jsonl"
        )
        with version_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(version, ensure_ascii=False, sort_keys=True) + "\n")

    def _scope_from_path(self, relative_path: str) -> str:
        parts = Path(relative_path).parts
        if len(parts) >= 3 and parts[0] == "assets":
            return f"asset:{parts[1]}"
        if len(parts) >= 3 and parts[0] == "hosts":
            return f"asset-host:{parts[1]}"
        if len(parts) >= 3 and parts[0] == "asset_kinds":
            return f"asset-kind:{parts[1]}"
        if len(parts) >= 3 and parts[0] == "sessions":
            return parts[1]
        return "global"

    def _preview(self, content: str) -> str:
        lines = [
            line.strip()
            for line in str(content or "").splitlines()
            if line.strip() and not line.startswith("- ") and not line.startswith("#")
        ]
        return "\n".join(lines[:4])[:360]

    def _parse_entries(self, scope_id: str, path: Path) -> list[dict[str, Any]]:
        content = path.read_text(encoding="utf-8")
        chunks = re.split(r"(?m)^##\s+", content)
        entries: list[dict[str, Any]] = []
        for chunk in chunks[1:]:
            entry = self._parse_entry_chunk(
                scope_id,
                path.relative_to(self.root_path).as_posix(),
                chunk,
            )
            if entry:
                entries.append(entry)
        return entries

    def _parse_entry_chunk(self, scope_id: str, relative_path: str, chunk: str) -> dict[str, Any] | None:
        lines = chunk.strip().splitlines()
        if not lines:
            return None
        timestamp = lines[0].strip()
        headers: dict[str, str] = {}
        summary_lines = []
        in_body = False
        for line in lines[1:]:
            if not in_body and line.strip() == "":
                in_body = True
                continue
            if not in_body and line.startswith("- ") and ":" in line:
                key, value = line[2:].split(":", 1)
                headers[key.strip()] = value.strip()
                continue
            if in_body:
                summary_lines.append(line)
        summary = "\n".join(summary_lines).strip()
        if not summary:
            return None
        metadata: dict[str, Any] = {}
        try:
            parsed = json.loads(headers.get("metadata") or "{}")
            if isinstance(parsed, dict):
                metadata = parsed
        except Exception:
            metadata = {}
        policy = self._classify_entry(summary, metadata)
        for key in (
            "memory_model",
            "memory_kind",
            "memory_kind_label",
            "retention_tier",
            "usage_role",
            "retrieval_enabled",
        ):
            if key in metadata:
                policy[key] = metadata[key]
        return {
            "scope_id": headers.get("scope_id") or scope_id,
            "timestamp": timestamp,
            "source_session_id": headers.get("source_session_id") or "",
            "metadata": metadata,
            "summary": summary,
            "summary_sha256": memory_content_sha256(summary),
            "path": relative_path,
            **policy,
        }

    def _candidate_id(self, relative_path: str, entry: dict[str, Any]) -> str:
        seed = "\n".join(
            [
                str(relative_path or ""),
                str(entry.get("timestamp") or ""),
                str(entry.get("source_session_id") or ""),
                str(entry.get("summary_sha256") or memory_content_sha256(entry.get("summary") or "")),
            ]
        )
        return f"memcand_{memory_content_sha256(seed)[:16]}"

    def _score_entry(self, entry: dict[str, Any], query: str) -> float:
        text = str(entry.get("summary") or "").lower()
        query_text = str(query or "").lower().strip()
        if not query_text:
            return 1.0
        score = 0.0
        if query_text in text:
            score += 10.0
        tokens = [token for token in re.split(r"\W+", query_text) if len(token) >= 2]
        for token in tokens:
            if token in text:
                score += 2.0
        for char in query_text:
            if "\u4e00" <= char <= "\u9fff" and char in text:
                score += 0.2
        return score or 0.1
