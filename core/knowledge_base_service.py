from __future__ import annotations

import os
import io
import json
import math
import re
import shutil
import asyncio
import hashlib
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class KnowledgeBaseServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


ALLOWED_KNOWLEDGE_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".log",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_KNOWLEDGE_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_SOURCE_PREVIEW_CHARS = 12000
DEFAULT_KNOWLEDGE_VAULT_DIR = Path("data") / "knowledge_vault"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vault_root() -> Path:
    return Path(os.getenv("OPSCORE_KNOWLEDGE_VAULT_DIR") or DEFAULT_KNOWLEDGE_VAULT_DIR)


def _manifest_path(vault_dir: Path) -> Path:
    return vault_dir / "state" / "sources.json"


def _safe_markdown_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _markdown_note_name(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", stem).strip("._-") or "source"


def _read_manifest(vault_dir: Path) -> list[dict[str, Any]]:
    path = _manifest_path(vault_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _write_manifest(vault_dir: Path, records: list[dict[str, Any]]) -> None:
    path = _manifest_path(vault_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    queue = [
        {
            "id": item.get("id"),
            "source_session_id": item.get("source_session_id"),
            "filename": item.get("filename"),
            "original_filename": item.get("original_filename"),
            "source_path": item.get("source_path"),
            "note_path": item.get("note_path"),
            "compile_status": item.get("compile_status"),
            "created_at": item.get("created_at"),
        }
        for item in records
        if item.get("compile_status") in {"pending_ai_compile", "analysis_ready", "awaiting_review"}
    ]
    (path.parent / "compile_queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_vault_skeleton(vault_dir: Path) -> None:
    for rel in (
        "raw/uploads",
        "wiki/sources",
        "wiki/assets",
        "wiki/sessions",
        "wiki/runbooks",
        "wiki/incidents",
        "wiki/profiles",
        "wiki/articles",
        "wiki/candidates",
        "wiki/canvases",
        "state",
    ):
        (vault_dir / rel).mkdir(parents=True, exist_ok=True)

    purpose_path = vault_dir / "purpose.md"
    if not purpose_path.exists():
        purpose_path.write_text(
            "\n".join(
                [
                    "# OpsCore Knowledge Vault Purpose",
                    "",
                    "这个知识库用于沉淀 OpsCore AI 运维平台的资产画像、巡检证据、故障经验、Runbook、会话结论和审计线索。",
                    "",
                    "辅助模型应优先把可复用、已验证、可追溯的内容编译成结构化 Markdown；不确定内容必须标记为 ambiguous，不得静默覆盖旧知识。",
                ]
            ),
            encoding="utf-8",
        )

    schema_path = vault_dir / "schema.md"
    if not schema_path.exists():
        schema_path.write_text(
            "\n".join(
                [
                    "# OpsCore LLM Wiki Schema",
                    "",
                    "## 三层结构",
                    "",
                    "- `raw/`：原始资料，只读留底，AI 不得修改。",
                    "- `wiki/`：AI 编译和人工维护的 Markdown 知识页，使用 YAML frontmatter 和 `[[wikilinks]]`。",
                    "- `state/`：可重建索引、图谱、编译队列和状态缓存，不作为唯一事实来源。",
                    "",
                    "## 编译流程",
                    "",
                    "1. 先分析原始资料，提取实体、资产、证据、风险、矛盾和建议。",
                    "2. 再写入 `wiki/candidates/` 或对应正式目录。",
                    "3. 新旧结论冲突时进入待确认，不得直接覆盖。",
                    "4. 每个结论必须保留来源路径、置信度和 extracted/inferred/ambiguous 标记。",
                ]
            ),
            encoding="utf-8",
        )


def _append_vault_log(vault_dir: Path, action: str, message: str) -> None:
    _ensure_vault_skeleton(vault_dir)
    log_path = vault_dir / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# OpsCore Knowledge Vault Log\n\n"
    line = f"## [{_utc_now_iso()}] {action} | {message}\n\n"
    log_path.write_text(existing.rstrip() + "\n\n" + line, encoding="utf-8")


def _write_vault_index(vault_dir: Path, records: list[dict[str, Any]]) -> None:
    _ensure_vault_skeleton(vault_dir)
    lines = [
        "---",
        'type: "vault-index"',
        f"sources: {len(records)}",
        "---",
        "",
        "# OpsCore Knowledge Vault",
        "",
        "这是 OpsCore 离线知识库的 Obsidian 兼容入口。原始资料保存在 `raw/`，AI 编译后的知识页会逐步补充到 `wiki/` 下的资产、Runbook、故障和画像目录。",
        "",
        "## 导航",
        "",
        "- [[purpose]]：知识库目标",
        "- [[schema]]：辅助模型维护规则",
        "- [[log]]：操作时间线",
        "",
        "## 原始资料",
    ]
    for item in sorted(records, key=lambda record: record.get("created_at", ""), reverse=True):
        title = item.get("original_filename") or item.get("filename") or "unknown"
        note_path = item.get("note_path") or ""
        status = item.get("compile_status") or item.get("status") or "pending"
        if note_path:
            lines.append(f"- [[{Path(note_path).stem}]] - {title} - {status}")
        else:
            lines.append(f"- {title} - {status}")
    lines.append("")
    (vault_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _register_vault_source(
    *,
    stored_file_path: str | os.PathLike[str],
    original_filename: str | None,
    safe_filename: str,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    _ensure_vault_skeleton(root)
    now = _utc_now_iso()
    day = now[:10]
    source_dir = root / "raw" / "uploads" / day
    note_dir = root / "wiki" / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    note_dir.mkdir(parents=True, exist_ok=True)

    source_path = source_dir / safe_filename
    if Path(stored_file_path).resolve() != source_path.resolve():
        shutil.copyfile(stored_file_path, source_path)

    note_name = f"{_markdown_note_name(safe_filename)}.md"
    note_path = note_dir / note_name
    source_rel = source_path.relative_to(root).as_posix()
    note_rel = note_path.relative_to(root).as_posix()
    record_id = f"src-{uuid.uuid4().hex[:12]}"
    source_session_id = f"source-session-{uuid.uuid4().hex[:12]}"
    record = {
        "id": record_id,
        "source_session_id": source_session_id,
        "filename": safe_filename,
        "original_filename": original_filename or safe_filename,
        "size": source_path.stat().st_size,
        "extension": source_path.suffix.lower(),
        "source_path": source_rel,
        "note_path": note_rel,
        "vault_path": str(root),
        "status": "vault_saved",
        "compile_status": "pending_ai_compile",
        "vector_status": "pending",
        "obsidian_compatible": True,
        "compile_stage": "uploaded",
        "created_at": now,
        "updated_at": now,
        "tags": ["source/upload", "opscore/knowledge"],
    }

    note_lines = [
        "---",
        f'id: "{record_id}"',
        f'source_session_id: "{source_session_id}"',
        'type: "source"',
        f'original_filename: "{_safe_markdown_value(record["original_filename"])}"',
        f'source_file: "{_safe_markdown_value(source_rel)}"',
        'compile_status: "pending_ai_compile"',
        'vector_status: "pending"',
        "tags:",
        "  - source/upload",
        "  - opscore/knowledge",
        "---",
        "",
        f"# {record['original_filename']}",
        "",
        "## 原始资料",
        "",
        f"- 文件：[[{source_rel}]]",
        f"- 上传时间：{now}",
        f"- 大小：{record['size']} bytes",
        "",
        "## AI 编译状态",
        "",
        "等待辅助模型按两阶段流程处理：先分析实体、证据、风险和矛盾，再生成候选 Wiki 页面，人工确认后进入正式知识目录。",
        "",
        "## 来源说明",
        "",
        "本页由 OpsCore 自动生成，原始文件不会被 AI 修改，后续编译结果需要保留来源引用。",
    ]
    note_path.write_text("\n".join(note_lines), encoding="utf-8")

    records = [item for item in _read_manifest(root) if item.get("filename") != safe_filename]
    records.append(record)
    _write_manifest(root, records)
    _write_vault_index(root, records)
    _append_vault_log(root, "upload", f"{record['original_filename']} -> {source_rel}")
    return record


def _update_vault_record(filename: str, **updates: Any) -> None:
    root = _vault_root()
    records = _read_manifest(root)
    changed = False
    for item in records:
        if item.get("filename") == filename:
            item.update(updates)
            item["updated_at"] = _utc_now_iso()
            changed = True
            break
    if changed:
        _write_manifest(root, records)
        _write_vault_index(root, records)


def _find_vault_record(identifier: str, vault_dir: str | os.PathLike[str] | None = None) -> tuple[Path, dict[str, Any]]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    for item in _read_manifest(root):
        if identifier in {
            str(item.get("id") or ""),
            str(item.get("source_session_id") or ""),
            str(item.get("filename") or ""),
        }:
            return root, item
    raise KnowledgeBaseServiceError(404, "待编译资料不存在")


def _read_source_preview(root: Path, record: dict[str, Any]) -> str:
    rel = record.get("source_path")
    if not rel:
        return ""
    path = root / str(rel)
    if path.suffix.lower() not in {".txt", ".md", ".log", ".csv", ".html", ".htm"}:
        return f"二进制或复杂格式文件：{record.get('original_filename') or record.get('filename')}，请辅助模型结合文件解析器或人工摘要继续编译。"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text[:MAX_SOURCE_PREVIEW_CHARS]


def _candidate_note_path(root: Path, record: dict[str, Any]) -> Path:
    base = _markdown_note_name(str(record.get("filename") or record.get("id") or "candidate"))
    return root / "wiki" / "candidates" / f"{base}.md"


def _article_note_path(root: Path, record: dict[str, Any]) -> Path:
    base = _markdown_note_name(str(record.get("filename") or record.get("id") or "article"))
    return root / "wiki" / "articles" / f"{base}.md"


def _replace_frontmatter_value(content: str, key: str, value: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return content
    replaced = False
    for index in range(1, end_index):
        if lines[index].startswith(f"{key}:"):
            lines[index] = f'{key}: "{_safe_markdown_value(value)}"'
            replaced = True
            break
    if not replaced:
        lines.insert(end_index, f'{key}: "{_safe_markdown_value(value)}"')
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _resolve_candidate_file(root: Path, record: dict[str, Any]) -> Path:
    candidate_rel = record.get("candidate_path")
    if not candidate_rel:
        raise KnowledgeBaseServiceError(400, "该资料还没有候选 Wiki 页面")
    path = (root / str(candidate_rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise KnowledgeBaseServiceError(400, "候选 Wiki 路径非法")
    if not path.exists():
        raise KnowledgeBaseServiceError(404, "候选 Wiki 页面不存在")
    return path


def _resolve_article_file(root: Path, record: dict[str, Any]) -> Path:
    article_rel = record.get("wiki_path")
    if not article_rel:
        raise KnowledgeBaseServiceError(400, "该资料还没有正式 Wiki 页面")
    path = (root / str(article_rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise KnowledgeBaseServiceError(400, "正式 Wiki 路径非法")
    if not path.exists():
        raise KnowledgeBaseServiceError(404, "正式 Wiki 页面不存在")
    return path


def _read_vault_text_file(root: Path, rel: str | None) -> str:
    if not rel:
        return ""
    path = (root / str(rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        return ""
    if not path.exists() or path.suffix.lower() not in {".md", ".txt", ".log", ".csv", ".html", ".htm"}:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _search_snippet(content: str, query: str, width: int = 180) -> str:
    if not content:
        return ""
    lower = content.lower()
    needle = query.lower()
    index = lower.find(needle)
    if index < 0:
        return content[:width].replace("\n", " ").strip()
    start = max(0, index - width // 2)
    end = min(len(content), index + len(query) + width // 2)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(content) else ""
    return (prefix + content[start:end] + suffix).replace("\n", " ").strip()


async def _generate_candidate_with_model(record: dict[str, Any], source_preview: str) -> str:
    from core.assistant_model_config import assistant_thinking_mode, resolve_assistant_model_id
    from core.llm_execution import execute_chat_stream

    model_id = resolve_assistant_model_id()
    messages = [
        {
            "role": "system",
            "content": (
                "你是 OpsCore 的辅助模型知识管家，负责把原始运维资料编译成 Obsidian 兼容 Markdown。"
                "必须使用中文，必须保留来源、置信度、证据、风险、建议动作和待确认事项。"
                "不确定内容标记为 ambiguous，不要伪造没有来源的数据。"
            ),
        },
        {
            "role": "user",
            "content": (
                "请把下面 source session 编译成一个候选 Wiki 页面，只输出 Markdown 正文。\n\n"
                f"source_session_id: {record.get('source_session_id')}\n"
                f"original_filename: {record.get('original_filename')}\n"
                f"source_path: {record.get('source_path')}\n"
                f"note_path: {record.get('note_path')}\n\n"
                "原始资料预览：\n"
                f"{source_preview or '暂无可读文本预览'}"
            ),
        },
    ]
    chunks: list[str] = []
    async def collect() -> str:
        async for chunk in execute_chat_stream(model_id, messages, assistant_thinking_mode(), tools=None):
            if chunk.get("type") == "content":
                chunks.append(str(chunk.get("content") or ""))
        return "".join(chunks).strip()

    return await asyncio.wait_for(collect(), timeout=45)


def _fallback_candidate_markdown(record: dict[str, Any], source_preview: str, reason: str = "") -> str:
    now = _utc_now_iso()
    title = record.get("original_filename") or record.get("filename") or "未命名资料"
    body = [
        f"# {title}",
        "",
        "## 编译状态",
        "",
        "- 状态：待人工确认",
        "- 编译方式：OpsCore 离线兜底候选页",
        f"- 编译时间：{now}",
    ]
    if reason:
        body.append(f"- 模型提示：{reason}")
    body.extend(
        [
            "",
            "## 来源",
            "",
            f"- Source Session：`{record.get('source_session_id') or record.get('id')}`",
            f"- 原始文件：`{record.get('source_path') or '-'}`",
            f"- 来源卡片：`{record.get('note_path') or '-'}`",
            "",
            "## 初步摘要",
            "",
            "该页面由 OpsCore 基于原始资料自动生成候选 Wiki，尚未经过辅助模型深度分析或人工确认。",
            "",
            "## 证据预览",
            "",
            "```text",
            (source_preview or "该文件暂未提取到可读文本预览。")[:MAX_SOURCE_PREVIEW_CHARS],
            "```",
            "",
            "## 待辅助模型补充",
            "",
            "- 关键实体和资产关系",
            "- 风险等级和证据链",
            "- 可复用 Runbook 或故障案例",
            "- 与现有知识的冲突检查",
        ]
    )
    return "\n".join(body)


async def compile_vault_source_candidate(
    identifier: str,
    *,
    use_ai: bool = True,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    _ensure_vault_skeleton(root)
    source_preview = _read_source_preview(root, record)
    model_status = "fallback"
    model_error = ""
    markdown = ""
    if use_ai:
        try:
            markdown = await _generate_candidate_with_model(record, source_preview)
            model_status = "ai_generated"
        except Exception as exc:
            model_error = str(exc)
    if not markdown:
        markdown = _fallback_candidate_markdown(record, source_preview, model_error)

    candidate_path = _candidate_note_path(root, record)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = [
        "---",
        f'id: "candidate-{uuid.uuid4().hex[:12]}"',
        'type: "wiki-candidate"',
        f'source_id: "{record.get("id")}"',
        f'source_session_id: "{record.get("source_session_id")}"',
        f'original_filename: "{_safe_markdown_value(str(record.get("original_filename") or ""))}"',
        f'source_file: "{_safe_markdown_value(str(record.get("source_path") or ""))}"',
        'review_status: "pending"',
        f'compile_model_status: "{model_status}"',
        "tags:",
        "  - wiki/candidate",
        "  - opscore/knowledge",
        "---",
        "",
    ]
    candidate_path.write_text("\n".join(frontmatter) + markdown.strip() + "\n", encoding="utf-8")

    records = _read_manifest(root)
    updated_record: dict[str, Any] | None = None
    for item in records:
        if item.get("id") == record.get("id"):
            item.update(
                {
                    "compile_status": "awaiting_review",
                    "compile_stage": "candidate_generated",
                    "candidate_path": candidate_path.relative_to(root).as_posix(),
                    "compiled_at": _utc_now_iso(),
                    "compile_model_status": model_status,
                    "compile_error": model_error,
                }
            )
            updated_record = item
            break
    if updated_record is None:
        updated_record = record
    _write_manifest(root, records)
    _write_vault_index(root, records)
    _append_vault_log(root, "compile-candidate", f"{record.get('original_filename')} -> {updated_record.get('candidate_path')}")
    return updated_record


def list_vault_candidates(vault_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    candidates: list[dict[str, Any]] = []
    for item in _read_manifest(root):
        candidate_path = item.get("candidate_path")
        if not candidate_path:
            continue
        path = root / str(candidate_path)
        candidates.append(
            {
                **item,
                "candidate_exists": path.exists(),
                "candidate_size": path.stat().st_size if path.exists() else 0,
                "review_status": "pending" if item.get("compile_status") == "awaiting_review" else item.get("compile_status"),
            }
        )
    return sorted(candidates, key=lambda item: str(item.get("compiled_at") or item.get("updated_at") or ""), reverse=True)


def list_vault_articles(vault_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    articles: list[dict[str, Any]] = []
    for item in _read_manifest(root):
        article_path = item.get("wiki_path")
        if not article_path:
            continue
        path = root / str(article_path)
        articles.append(
            {
                **item,
                "article_exists": path.exists(),
                "article_size": path.stat().st_size if path.exists() else 0,
                "review_status": "approved" if item.get("compile_status") == "approved" else item.get("compile_status"),
            }
        )
    return sorted(articles, key=lambda item: str(item.get("approved_at") or item.get("updated_at") or ""), reverse=True)


def read_vault_article(
    identifier: str,
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    article_path = _resolve_article_file(root, record)
    content = article_path.read_text(encoding="utf-8")
    return {
        **record,
        "content": content,
        "content_sha256": _sha256_text(content),
        "article_size": article_path.stat().st_size,
        "article_exists": True,
    }


def search_vault_knowledge(
    query: str,
    *,
    scope: str = "all",
    limit: int = 20,
    vault_dir: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    term = query.strip()
    if not term:
        raise KnowledgeBaseServiceError(400, "搜索关键词不能为空")
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    scope = scope if scope in {"all", "articles", "candidates", "sources", "raw"} else "all"
    results: list[dict[str, Any]] = []
    searchable_fields = [
        ("articles", "正式 Wiki", "wiki_path"),
        ("candidates", "候选 Wiki", "candidate_path"),
        ("sources", "来源卡片", "note_path"),
        ("raw", "原始资料", "source_path"),
    ]
    for record in _read_manifest(root):
        title = str(record.get("original_filename") or record.get("filename") or record.get("id") or "unknown")
        metadata_blob = " ".join(
            str(record.get(key) or "")
            for key in (
                "id",
                "source_session_id",
                "filename",
                "original_filename",
                "source_path",
                "note_path",
                "candidate_path",
                "wiki_path",
                "compile_status",
                "compile_stage",
            )
        )
        for kind, kind_label, path_key in searchable_fields:
            if scope != "all" and scope != kind:
                continue
            rel = record.get(path_key)
            if not rel:
                continue
            content = _read_vault_text_file(root, str(rel))
            haystack = f"{metadata_blob}\n{content}"
            if term.lower() not in haystack.lower():
                continue
            score = 1
            if term.lower() in title.lower():
                score += 5
            if term.lower() in metadata_blob.lower():
                score += 2
            if content and term.lower() in content.lower():
                score += 3
            results.append(
                {
                    "id": record.get("id"),
                    "source_session_id": record.get("source_session_id"),
                    "title": title,
                    "kind": kind,
                    "kind_label": kind_label,
                    "path": rel,
                    "compile_status": record.get("compile_status"),
                    "compile_stage": record.get("compile_stage"),
                    "snippet": _search_snippet(content or metadata_blob, term),
                    "score": score,
                    "updated_at": record.get("updated_at") or record.get("approved_at") or record.get("compiled_at"),
                }
            )
    results.sort(key=lambda item: (int(item.get("score") or 0), str(item.get("updated_at") or "")), reverse=True)
    return results[:limit]


def build_vault_knowledge_graph(
    *,
    include_candidates: bool = True,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    records = list_vault_articles(root)
    if include_candidates:
        records += list_vault_candidates(root)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    by_path: dict[str, dict[str, Any]] = {}
    by_title: dict[str, dict[str, Any]] = {}

    for record in records:
        rel_path = record.get("wiki_path") or record.get("candidate_path")
        if not rel_path:
            continue
        title = record.get("original_filename") or record.get("filename") or Path(str(rel_path)).stem
        kind = "article" if record.get("wiki_path") else "candidate"
        node = {
            "id": str(rel_path),
            "title": str(title),
            "kind": kind,
            "kind_label": "正式知识" if kind == "article" else "候选草稿",
            "path": str(rel_path),
            "source_session_id": record.get("source_session_id") or record.get("id"),
            "compile_stage": record.get("compile_stage"),
            "review_status": record.get("review_status"),
            "updated_at": record.get("approved_at") or record.get("compiled_at") or record.get("created_at"),
            "degree": 0,
            "links_in": 0,
            "links_out": 0,
        }
        nodes.append(node)
        by_path[str(rel_path).lower()] = node
        by_title[str(title).lower()] = node
        by_title[Path(str(rel_path)).stem.lower()] = node

    seen_edges: set[tuple[str, str, str]] = set()

    def add_edge(source: dict[str, Any], target: dict[str, Any], kind: str, label: str) -> None:
        if source["id"] == target["id"]:
            return
        edge_key = (source["id"], target["id"], kind)
        if edge_key in seen_edges:
            return
        edges.append(
            {
                "source": source["id"],
                "target": target["id"],
                "kind": kind,
                "label": label,
            }
        )
        seen_edges.add(edge_key)
        source["links_out"] = int(source.get("links_out") or 0) + 1
        target["links_in"] = int(target.get("links_in") or 0) + 1

    for node in nodes:
        content = _read_vault_text_file(root, node["path"])
        if not content:
            continue
        for link in re.findall(r"\[\[([^\]\|#]+)(?:[^\]]*)\]\]", content):
            target_key = link.strip().lower()
            target = by_title.get(target_key) or by_path.get(target_key) or by_path.get(f"wiki/articles/{target_key}.md")
            if target:
                add_edge(node, target, "wikilink", "[[]] 双链")
        lower_content = content.lower()
        for target in nodes:
            if target["id"] == node["id"]:
                continue
            title = str(target["title"]).lower()
            if title and title in lower_content:
                add_edge(node, target, "mention", "内容提及")

    relation_counts: dict[str, int] = {}
    for edge in edges:
        kind = str(edge.get("kind") or "unknown")
        relation_counts[kind] = relation_counts.get(kind, 0) + 1

    ranked_nodes = sorted(nodes, key=lambda item: (int(item.get("links_in") or 0) + int(item.get("links_out") or 0), str(item.get("title") or "")), reverse=True)
    total = len(ranked_nodes)
    for index, node in enumerate(ranked_nodes):
        degree = int(node.get("links_in") or 0) + int(node.get("links_out") or 0)
        node["degree"] = degree
        if total <= 1:
            node["x"] = 50
            node["y"] = 32
        elif index == 0 and degree > 0:
            node["x"] = 50
            node["y"] = 32
        else:
            angle = (2 * 3.141592653589793 * index) / total
            node["x"] = round(50 + 34 * math.cos(angle), 2)
            node["y"] = round(32 + 22 * math.sin(angle), 2)
        node["size"] = min(18, 7 + degree * 2 + (2 if node.get("kind") == "article" else 0))

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "article_count": len([node for node in nodes if node["kind"] == "article"]),
            "candidate_count": len([node for node in nodes if node["kind"] == "candidate"]),
            "linked_node_count": len([node for node in nodes if int(node.get("degree") or 0) > 0]),
            "isolated_node_count": len([node for node in nodes if int(node.get("degree") or 0) == 0]),
            "relation_counts": relation_counts,
            "generated_at": _utc_now_iso(),
        },
    }


def create_vault_export_zip(
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> Path:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    _ensure_vault_skeleton(root)
    export_dir = root / "state" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = export_dir / f"opscore-knowledge-vault-{timestamp}.zip"
    export_dir_resolved = export_dir.resolve()

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if export_dir_resolved in resolved.parents or resolved == export_dir_resolved:
                continue
            archive.write(path, path.relative_to(root).as_posix())

    return archive_path


def import_vault_archive(
    file_bytes: bytes,
    *,
    filename: str = "vault.zip",
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if not filename.lower().endswith(".zip"):
        raise KnowledgeBaseServiceError(400, "仅支持导入 .zip 格式的 Vault 归档")
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    _ensure_vault_skeleton(root)
    root_resolved = root.resolve()
    imported: list[str] = []
    skipped: list[str] = []

    try:
        archive = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile as exc:
        raise KnowledgeBaseServiceError(400, "Vault ZIP 文件无法解析") from exc

    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            parts = [part for part in name.split("/") if part and part != "."]
            if not parts or any(part == ".." for part in parts):
                skipped.append(name)
                continue
            if len(parts) >= 2 and parts[0] == "state" and parts[1] == "exports":
                skipped.append(name)
                continue
            target = (root / Path(*parts)).resolve()
            if root_resolved not in target.parents and target != root_resolved:
                skipped.append(name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            imported.append("/".join(parts))

    _ensure_vault_skeleton(root)
    return {
        "filename": filename,
        "imported_count": len(imported),
        "skipped_count": len(skipped),
        "imported": imported,
        "skipped": skipped,
    }


def read_vault_candidate(
    identifier: str,
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    candidate_path = _resolve_candidate_file(root, record)
    content = candidate_path.read_text(encoding="utf-8")
    return {
        **record,
        "content": content,
        "content_sha256": _sha256_text(content),
        "candidate_size": candidate_path.stat().st_size,
        "candidate_exists": True,
    }


def update_vault_candidate(
    identifier: str,
    *,
    content: str,
    content_sha256: str | None = None,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if not content.strip():
        raise KnowledgeBaseServiceError(400, "候选 Wiki 内容不能为空")
    root, record = _find_vault_record(identifier, vault_dir)
    candidate_path = _resolve_candidate_file(root, record)
    current = candidate_path.read_text(encoding="utf-8")
    if content_sha256 and content_sha256 != _sha256_text(current):
        raise KnowledgeBaseServiceError(409, "候选 Wiki 已被其他操作修改，请刷新后重试")
    candidate_path.write_text(content, encoding="utf-8")

    records = _read_manifest(root)
    updated_record: dict[str, Any] | None = None
    for item in records:
        if item.get("id") == record.get("id"):
            item.update(
                {
                    "compile_stage": "candidate_edited",
                    "compile_status": "awaiting_review",
                    "edited_at": _utc_now_iso(),
                }
            )
            updated_record = item
            break
    if updated_record is None:
        updated_record = record
    _write_manifest(root, records)
    _write_vault_index(root, records)
    _append_vault_log(root, "edit-candidate", str(record.get("original_filename") or record.get("filename") or identifier))
    return read_vault_candidate(str(updated_record.get("source_session_id") or updated_record.get("id")), vault_dir=root)


def approve_vault_candidate(
    identifier: str,
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    candidate_rel = record.get("candidate_path")
    if not candidate_rel:
        raise KnowledgeBaseServiceError(400, "该资料还没有候选 Wiki 页面")
    candidate_path = root / str(candidate_rel)
    if not candidate_path.exists():
        raise KnowledgeBaseServiceError(404, "候选 Wiki 页面不存在")

    article_path = _article_note_path(root, record)
    article_path.parent.mkdir(parents=True, exist_ok=True)
    content = candidate_path.read_text(encoding="utf-8")
    content = _replace_frontmatter_value(content, "type", "wiki-article")
    content = _replace_frontmatter_value(content, "review_status", "approved")
    content = _replace_frontmatter_value(content, "approved_at", _utc_now_iso())
    article_path.write_text(content, encoding="utf-8")

    records = _read_manifest(root)
    updated_record: dict[str, Any] | None = None
    for item in records:
        if item.get("id") == record.get("id"):
            item.update(
                {
                    "compile_status": "approved",
                    "compile_stage": "wiki_approved",
                    "wiki_path": article_path.relative_to(root).as_posix(),
                    "approved_at": _utc_now_iso(),
                }
            )
            updated_record = item
            break
    if updated_record is None:
        updated_record = record
    _write_manifest(root, records)
    _write_vault_index(root, records)
    _append_vault_log(root, "approve-candidate", f"{record.get('original_filename')} -> {updated_record.get('wiki_path')}")
    return updated_record


def list_vault_source_records(vault_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    return _read_manifest(root)


def list_vault_compile_queue(vault_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    queue_path = root / "state" / "compile_queue.json"
    if not queue_path.exists():
        return []
    try:
        queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(queue_data, list):
        return []

    sources_by_id = {
        str(item.get("id")): item
        for item in _read_manifest(root)
        if item.get("id")
    }
    items: list[dict[str, Any]] = []
    for entry in queue_data:
        if not isinstance(entry, dict):
            continue
        source = sources_by_id.get(str(entry.get("id")), {})
        merged = {**source, **entry}
        merged.setdefault("compile_status", "pending_ai_compile")
        merged.setdefault("compile_stage", source.get("compile_stage") or "queued")
        merged.setdefault("status_label", "等待辅助模型编译")
        items.append(merged)
    return sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def remove_vault_source_record(filename: str, vault_dir: str | os.PathLike[str] | None = None) -> bool:
    root = Path(vault_dir) if vault_dir is not None else _vault_root()
    records = _read_manifest(root)
    target = next((item for item in records if item.get("filename") == filename), None)
    if not target:
        return False
    for key in ("source_path", "note_path"):
        rel = target.get(key)
        if not rel:
            continue
        try:
            path = (root / rel).resolve()
            if root.resolve() in path.parents or path == root.resolve():
                path.unlink(missing_ok=True)
        except OSError:
            pass
    remaining = [item for item in records if item.get("filename") != filename]
    _write_manifest(root, remaining)
    _write_vault_index(root, remaining)
    _append_vault_log(root, "delete", str(target.get("original_filename") or filename))
    return True


def safe_knowledge_filename(original_filename: str | None) -> str:
    original_name = os.path.basename(original_filename or "")
    stem, ext = os.path.splitext(original_name)
    normalized_ext = ext.lower()
    if normalized_ext not in ALLOWED_KNOWLEDGE_EXTENSIONS:
        raise KnowledgeBaseServiceError(
            415,
            f"不支持的知识库文件类型: {normalized_ext or 'unknown'}",
        )

    safe_stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", stem).strip("._-") or "document"
    return f"{safe_stem}-{uuid.uuid4().hex[:8]}{normalized_ext}"


def persist_knowledge_upload(upload_file, kb_dir: str | os.PathLike[str], safe_filename: str) -> str:
    file_path = Path(kb_dir) / safe_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with file_path.open("wb") as buffer:
        while True:
            chunk = upload_file.file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_KNOWLEDGE_UPLOAD_BYTES:
                buffer.close()
                try:
                    file_path.unlink()
                except OSError:
                    pass
                raise KnowledgeBaseServiceError(413, "知识库文件超过 50MB 限制")
            buffer.write(chunk)
    return str(file_path)


def _resolve_kb_manager(kb_manager=None):
    if kb_manager is not None:
        return kb_manager
    from core.rag import kb_manager as default_kb_manager

    return default_kb_manager


async def ingest_knowledge_document(kb_manager_or_upload_file, upload_file=None) -> str:
    if upload_file is None:
        kb_manager = _resolve_kb_manager()
        upload_file = kb_manager_or_upload_file
    else:
        kb_manager = _resolve_kb_manager(kb_manager_or_upload_file)

    safe_filename = safe_knowledge_filename(upload_file.filename)
    try:
        file_path = persist_knowledge_upload(upload_file, kb_manager.kb_dir, safe_filename)
        vault_record = _register_vault_source(
            stored_file_path=file_path,
            original_filename=upload_file.filename,
            safe_filename=safe_filename,
        )
        from core.llm_factory import get_embedding_client_and_model

        client, embedding_model = get_embedding_client_and_model()
        result = await kb_manager.ingest_document(file_path, client, embedding_model)
    except KnowledgeBaseServiceError:
        raise
    except Exception as exc:
        detail = str(exc)
        if "vault_record" in locals():
            _update_vault_record(safe_filename, vector_status="skipped", vector_error=detail)
            return f"已保存到 Obsidian Vault，等待 AI 编译；向量注入跳过：{detail}"
        raise KnowledgeBaseServiceError(500, detail) from exc

    if result.get("status") == "success":
        _update_vault_record(safe_filename, vector_status="indexed")
        return str(result.get("message") or "")
    message = str(result.get("message") or "文档内容提取或向量化失败")
    _update_vault_record(safe_filename, vector_status="failed", vector_error=message)
    return f"已保存到 Obsidian Vault，等待 AI 编译；向量注入失败：{message}"


async def list_knowledge_document_records(kb_manager=None) -> list[Any]:
    kb_manager = _resolve_kb_manager(kb_manager)
    vault_records = list_vault_source_records()
    try:
        kb_records = await kb_manager.list_documents()
    except Exception as exc:
        if vault_records:
            return vault_records
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    merged: dict[str, Any] = {}
    for item in vault_records:
        if isinstance(item, dict) and item.get("filename"):
            merged[str(item["filename"])] = item
    for item in kb_records:
        if isinstance(item, dict):
            filename = str(item.get("filename") or item.get("name") or "")
            if filename and filename in merged:
                merged[filename] = {**merged[filename], **item}
            elif filename:
                merged[filename] = item
        else:
            filename = str(item)
            merged.setdefault(filename, {"filename": filename, "status": "legacy_vector"})
    return list(merged.values())


async def remove_knowledge_document_record(kb_manager_or_filename, filename: str | None = None) -> str:
    if filename is None:
        kb_manager = _resolve_kb_manager()
        filename = str(kb_manager_or_filename)
    else:
        kb_manager = _resolve_kb_manager(kb_manager_or_filename)

    try:
        result = await kb_manager.delete_document(filename)
    except Exception as exc:
        removed_from_vault = remove_vault_source_record(filename)
        if removed_from_vault:
            return f"已从 Obsidian Vault 移除 {filename}"
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    removed_from_vault = remove_vault_source_record(filename)
    if result.get("status") == "success":
        return str(result.get("message") or "")
    if removed_from_vault:
        return f"已从 Obsidian Vault 移除 {filename}"
    raise KnowledgeBaseServiceError(404, str(result.get("message") or "知识库文档不存在"))
