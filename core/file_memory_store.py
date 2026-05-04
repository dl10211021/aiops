from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_MEMORY_STORES = [
    {
        "id": "global",
        "name": "全局只读记忆",
        "description": "平台规则、组织规范和长期参考资料。默认只读，避免被会话污染。",
        "path_prefix": "global/",
        "access": "read_only",
        "lifecycle": "long_term",
        "instructions": "仅作为高可信参考资料读取；不得由普通会话写入。遇到冲突时，以当前资产实时证据和用户最新确认优先。",
    },
    {
        "id": "sessions",
        "name": "会话记忆",
        "description": "单次会话产生的上下文、阶段性经验和反馈。",
        "path_prefix": "sessions/",
        "access": "read_write",
        "lifecycle": "session_scoped",
        "instructions": "用于保存本会话被验证过的偏好、纠错和阶段结论；写入前必须压缩为小而准的中文记忆，避免流水账。",
    },
    {
        "id": "assets",
        "name": "资产记忆",
        "description": "同一资产的画像、巡检经验、风险和纠错记录。",
        "path_prefix": "assets/",
        "access": "read_write",
        "lifecycle": "asset_scoped",
        "instructions": "用于同一资产跨会话复用；只保存经过原生协议工具验证的资产画像、风险例外、巡检经验和用户纠错。",
    },
    {
        "id": "hosts",
        "name": "主机记忆",
        "description": "同一主机地址复用的运维经验。",
        "path_prefix": "hosts/",
        "access": "read_write",
        "lifecycle": "host_scoped",
        "instructions": "用于同一 IP/主机的长期经验；读取后必须结合当前时间、当前会话和实时巡检结果复核，不能直接当作事实执行。",
    },
    {
        "id": "asset_kinds",
        "name": "资产类型记忆",
        "description": "同类协议或资产类型共享的通用经验。",
        "path_prefix": "asset_kinds/",
        "access": "read_write",
        "lifecycle": "type_scoped",
        "instructions": "用于 Linux、Windows、Oracle、交换机等同类资产的通用方法；仅提供操作思路，不覆盖具体资产证据。",
    },
]


def safe_memory_segment(value: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    segment = segment.strip("._-")
    return segment[:96] or "default"


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
        relative_path = memory_scope_path(scope_id)
        target_path = self._resolve_memory_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        metadata = dict(metadata or {})
        summary = str(summary or "").strip()
        if not summary:
            raise ValueError("memory summary is empty")

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
            entries.extend(self._parse_entries(scope_id, path))

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
            memories.append(
                {
                    "path": relative_path,
                    "scope_id": self._scope_from_path(relative_path),
                    "store_id": store["id"],
                    "store_name": store["name"],
                    "access": store["access"],
                    "size": path.stat().st_size,
                    "entries": len(entries),
                    "updated_at": datetime.datetime.fromtimestamp(
                        path.stat().st_mtime
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "preview": self._preview(content),
                }
            )
        return memories

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
        return self._load_store_registry()

    def read_memory(self, path: str) -> dict[str, Any]:
        self.initialize()
        relative_path = self._safe_relative_path(path)
        target = self._resolve_memory_path(relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path)
        content = target.read_text(encoding="utf-8")
        return {
            "path": relative_path.as_posix(),
            "scope_id": self._scope_from_path(relative_path.as_posix()),
            "store_id": self._store_for_path(relative_path.as_posix())["id"],
            "store_name": self._store_for_path(relative_path.as_posix())["name"],
            "access": self._store_for_path(relative_path.as_posix())["access"],
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
        stores = self._load_store_registry()
        for store in stores:
            prefix = str(store.get("path_prefix") or "").lstrip("/")
            if prefix and normalized.startswith(prefix):
                return store
        return stores[0] if stores else DEFAULT_MEMORY_STORES[0]

    def _version_id(self, timestamp: str, path: str, operation: str, content: str) -> str:
        digest = memory_content_sha256(f"{timestamp}\n{path}\n{operation}\n{content}")[:16]
        return f"memver_{digest}"

    def _initial_header(self, scope_id: str) -> str:
        return (
            "# OpsCore Memory Store\n\n"
            f"- scope_id: {scope_id}\n"
            "- access: read_write\n"
            "- rule: historical memory only, verify with live tools before acting\n\n"
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
            summary_lines = []
            in_body = False
            for line in lines[1:]:
                if not in_body and line.strip() == "":
                    in_body = True
                    continue
                if in_body:
                    summary_lines.append(line)
            summary = "\n".join(summary_lines).strip()
            if summary:
                entries.append(
                    {
                        "scope_id": scope_id,
                        "timestamp": timestamp,
                        "summary": summary,
                        "summary_sha256": memory_content_sha256(summary),
                        "path": path.relative_to(self.root_path).as_posix(),
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
