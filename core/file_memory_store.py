from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any


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

    def mark_reviewed(self, path: str, *, actor: str = "user") -> dict[str, Any]:
        detail = self.read_memory(path)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            content=str(detail.get("content") or "").rstrip() + review_entry,
            content_sha256=str(detail.get("content_sha256") or ""),
            actor=f"memory_review:{actor}",
        )

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
            lines = chunk.strip().splitlines()
            if not lines:
                continue
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
            if summary:
                metadata: dict[str, Any] = {}
                try:
                    parsed = json.loads(headers.get("metadata") or "{}")
                    if isinstance(parsed, dict):
                        metadata = parsed
                except Exception:
                    metadata = {}
                policy = self._classify_entry(summary, metadata)
                entry_scope = headers.get("scope_id") or scope_id
                entries.append(
                    {
                        "scope_id": entry_scope,
                        "timestamp": timestamp,
                        "source_session_id": headers.get("source_session_id") or "",
                        "metadata": metadata,
                        "summary": summary,
                        "summary_sha256": memory_content_sha256(summary),
                        "path": path.relative_to(self.root_path).as_posix(),
                        **policy,
                    }
                )
        return entries

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
