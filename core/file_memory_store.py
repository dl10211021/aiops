from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any


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
            "timestamp": now,
            "operation": "modified" if existed else "created",
            "path": relative_path.as_posix(),
            "scope_id": scope_id,
            "source_session_id": source_session_id,
            "content_sha256": memory_content_sha256(new_content),
            "summary_sha256": memory_content_sha256(summary),
            "metadata": metadata,
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

    def _resolve_memory_path(self, relative_path: Path) -> Path:
        target = (self.root_path / relative_path).resolve()
        root = self.root_path.resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("memory path escapes store root") from exc
        return target

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
