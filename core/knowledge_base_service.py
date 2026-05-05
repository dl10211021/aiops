from __future__ import annotations

import os
import io
import json
import math
import re
import shutil
import asyncio
import hashlib
import inspect
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
MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS = 60000
DEFAULT_KNOWLEDGE_VAULT_DIR = Path("data") / "knowledge_vault"
TEXT_PREVIEW_EXTENSIONS = {".txt", ".md", ".log", ".csv", ".html", ".htm", ".json", ".yml", ".yaml", ".xml"}


class _KnowledgeUploadStorage:
    kb_dir = "knowledge_base"


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
        "等待辅助模型按两阶段流程处理：先分析实体、证据、风险和矛盾，再生成AI 摘要页面，确认后进入 RAG 资料目录。",
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


def _resolve_vault_record_path(root: Path, rel: str | None, label: str) -> Path:
    if not rel:
        raise KnowledgeBaseServiceError(404, f"{label}不存在")
    path = (root / str(rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise KnowledgeBaseServiceError(400, f"{label}路径非法")
    if not path.exists() or not path.is_file():
        raise KnowledgeBaseServiceError(404, f"{label}不存在")
    return path


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


def read_knowledge_document_record(
    identifier: str,
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    source_path = _resolve_vault_record_path(root, record.get("source_path"), "资料原文")
    extension = source_path.suffix.lower()
    preview_available = extension in TEXT_PREVIEW_EXTENSIONS
    content_type = "text" if preview_available else "metadata"
    content = ""
    truncated = False

    if preview_available:
        try:
            raw_content = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise KnowledgeBaseServiceError(500, "读取资料原文失败") from exc
        truncated = len(raw_content) > MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS
        content = raw_content[:MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS]
    else:
        note_content = _read_vault_text_file(root, record.get("note_path"))
        if note_content:
            content = note_content[:MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS]
            truncated = len(note_content) > MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS
            content_type = "source_note"
        else:
            content = (
                f"该资料是 {extension or '未知'} 格式，当前页面暂不直接预览二进制或复杂格式原文。\n"
                "文件已经保存在资料库，可用于后续解析、检索或导出备份。"
            )

    return {
        **record,
        "content": content,
        "content_sha256": _sha256_text(content),
        "content_type": content_type,
        "preview_available": preview_available,
        "truncated": truncated,
        "preview_limit": MAX_KNOWLEDGE_CONTENT_PREVIEW_CHARS,
        "extension": extension or record.get("extension"),
    }


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
        raise KnowledgeBaseServiceError(400, "该资料还没有 AI 摘要页面")
    path = (root / str(candidate_rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise KnowledgeBaseServiceError(400, "AI 摘要路径非法")
    if not path.exists():
        raise KnowledgeBaseServiceError(404, "AI 摘要页面不存在")
    return path


def _resolve_article_file(root: Path, record: dict[str, Any]) -> Path:
    article_rel = record.get("wiki_path")
    if not article_rel:
        raise KnowledgeBaseServiceError(400, "该资料还没有RAG 资料 页面")
    path = (root / str(article_rel)).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise KnowledgeBaseServiceError(400, "RAG 资料路径非法")
    if not path.exists():
        raise KnowledgeBaseServiceError(404, "RAG 资料 页面不存在")
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
                "请把下面 source session 编译成一个 AI 摘要页面，只输出 Markdown 正文。\n\n"
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
        "- 状态：待确认",
        "- 编译方式：OpsCore 离线兜底摘要",
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
            f"- 来源记录：`{record.get('note_path') or '-'}`",
            "",
            "## 初步摘要",
            "",
            "该页面由 OpsCore 基于原始资料自动生成 AI 摘要，尚未经过辅助模型深度分析或确认。",
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
        ("articles", "RAG 资料", "wiki_path"),
        ("candidates", "AI 摘要", "candidate_path"),
        ("sources", "来源记录", "note_path"),
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


_SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key|api_token|"
    r"密码|口令|密钥|令牌)\b\s*[:=：]\s*([^\s,;，；]+)"
)
_SENSITIVE_TABLE_TOKENS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "api_token",
    "密码",
    "口令",
    "密钥",
    "令牌",
}


def redact_sensitive_rag_text(text: str) -> str:
    """Hide obvious credentials before RAG snippets are injected into model context."""
    if not text:
        return ""

    def replace_field(match: re.Match[str]) -> str:
        label = match.group(1)
        separator = "：" if "：" in match.group(0) else ":"
        return f"{label}{separator} [已隐藏]"

    redacted = _SENSITIVE_FIELD_PATTERN.sub(replace_field, text)
    safe_lines: list[str] = []
    for line in redacted.splitlines():
        parts = line.split()
        hidden = False
        for index, part in enumerate(parts):
            normalized = part.strip(":：=").lower()
            if normalized in _SENSITIVE_TABLE_TOKENS and index < len(parts) - 1:
                safe_lines.append(" ".join(parts[: index + 1] + ["[已隐藏]"]))
                hidden = True
                break
        if not hidden:
            safe_lines.append(line)
    return "\n".join(safe_lines)


def build_vault_rag_context_for_prompt(
    query: str,
    *,
    limit: int = 4,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Build a compact, redacted RAG evidence block for chat prompt injection."""
    results = search_vault_knowledge(query, scope="all", limit=max(1, limit), vault_dir=vault_dir)
    references: list[dict[str, Any]] = []
    lines = [
        "[OpsCore RAG 证据上下文]",
        "以下内容来自 OpsCore RAG 资料库，已做敏感字段脱敏。回答时优先引用这些证据；证据不足时必须明确说明，不要编造。",
    ]
    for index, item in enumerate(results, start=1):
        title = redact_sensitive_rag_text(str(item.get("title") or "未命名资料"))
        kind_label = str(item.get("kind_label") or item.get("kind") or "资料")
        path = str(item.get("path") or "-")
        snippet = redact_sensitive_rag_text(str(item.get("snippet") or "")).strip()
        if not snippet:
            continue
        lines.append(f"{index}. {kind_label} | {title} | {path}")
        lines.append(f"   证据摘要：{snippet}")
        references.append(
            {
                "source_type": "rag",
                "kind": item.get("kind"),
                "kind_label": kind_label,
                "title": title,
                "path": path,
                "source_session_id": item.get("source_session_id"),
                "summary_preview": snippet[:240],
                "score": item.get("score"),
                "updated_at": item.get("updated_at"),
            }
        )

    if not references:
        return {"context": "", "references": []}
    return {"context": "\n".join(lines), "references": references}


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
    seen_node_ids: set[str] = set()

    for record in records:
        rel_path = record.get("wiki_path") or record.get("candidate_path")
        if not rel_path:
            continue
        node_id = str(rel_path)
        node_key = node_id.lower()
        if node_key in seen_node_ids:
            continue
        seen_node_ids.add(node_key)
        title = record.get("original_filename") or record.get("filename") or Path(str(rel_path)).stem
        kind = "article" if record.get("wiki_path") else "candidate"
        node = {
            "id": node_id,
            "title": str(title),
            "kind": kind,
            "kind_label": "RAG 资料" if kind == "article" else "AI 摘要",
            "path": node_id,
            "source_session_id": record.get("source_session_id") or record.get("id"),
            "compile_stage": record.get("compile_stage"),
            "review_status": record.get("review_status"),
            "updated_at": record.get("approved_at") or record.get("compiled_at") or record.get("created_at"),
            "degree": 0,
            "links_in": 0,
            "links_out": 0,
        }
        nodes.append(node)
        by_path[node_key] = node
        by_title[str(title).lower()] = node
        by_title[Path(node_id).stem.lower()] = node

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
        raise KnowledgeBaseServiceError(400, "AI 摘要内容不能为空")
    root, record = _find_vault_record(identifier, vault_dir)
    candidate_path = _resolve_candidate_file(root, record)
    current = candidate_path.read_text(encoding="utf-8")
    if content_sha256 and content_sha256 != _sha256_text(current):
        raise KnowledgeBaseServiceError(409, "AI 摘要已被其他操作修改，请刷新后重试")
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
        raise KnowledgeBaseServiceError(400, "该资料还没有 AI 摘要页面")
    candidate_path = root / str(candidate_rel)
    if not candidate_path.exists():
        raise KnowledgeBaseServiceError(404, "AI 摘要页面不存在")

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


def remove_legacy_knowledge_upload_copy(kb_manager, filename: str) -> bool:
    """Remove the compatibility copy under kb_manager.kb_dir after a document is deleted."""
    kb_dir_value = getattr(kb_manager, "kb_dir", None)
    if not kb_dir_value:
        return False
    try:
        kb_dir = Path(kb_dir_value).resolve()
        target = (kb_dir / filename).resolve()
        if kb_dir not in target.parents or target == kb_dir:
            return False
        if not target.exists():
            return False
        target.unlink()
        return True
    except OSError:
        return False


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


def _resolve_kb_manager(kb_manager=None, *, materialize: bool = True):
    if kb_manager is not None:
        return kb_manager
    from core.rag import kb_manager as default_kb_manager

    materialize_manager = getattr(default_kb_manager, "materialize", None)
    if materialize and callable(materialize_manager):
        return materialize_manager()
    return default_kb_manager


def _resolve_knowledge_embedding_client_and_model():
    from core.embedding_config import get_embedding_config

    configured_model, _ = get_embedding_config()
    model_id = os.environ.get("EMBEDDING_MODEL_ID") or configured_model
    model_id = str(model_id or "").strip()
    if not model_id:
        return None

    from core.llm_factory import get_embedding_client_and_model

    return get_embedding_client_and_model(model_id)


def _is_local_embedding_configured() -> bool:
    try:
        from core.embedding_config import get_embedding_config
        from core.local_embedding import is_local_embedding_model_id

        embedding_model, _ = get_embedding_config()
        return is_local_embedding_model_id(embedding_model)
    except Exception:
        return False


def _knowledge_reindex_timeout_seconds() -> float:
    default_seconds = 180.0 if _is_local_embedding_configured() else 10.0

    raw_value = os.environ.get("OPSCORE_KNOWLEDGE_REINDEX_TIMEOUT_SECONDS")
    try:
        seconds = float(raw_value) if raw_value else default_seconds
    except (TypeError, ValueError):
        seconds = default_seconds
    return max(0.1, min(seconds, 600.0))


def _knowledge_setup_timeout_seconds(timeout_seconds: float) -> float:
    setup_cap = 120.0 if _is_local_embedding_configured() else 3.0
    return min(timeout_seconds, setup_cap)


def _run_knowledge_ingest_blocking(kb_manager, file_path: str, client: Any, embedding_model: str):
    result = kb_manager.ingest_document(file_path, client, embedding_model)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _friendly_vector_message(message: str) -> str:
    detail = str(message or "").strip()
    if not detail:
        return "RAG 索引未完成；资料已保存，可用于原文检索。"
    lower_detail = detail.lower()
    if (
        "error code: 404" in lower_detail
        or "model_not_found" in lower_detail
        or "model not found" in lower_detail
        or "向量模型调用失败" in detail
    ):
        return "向量模型不可用或名称不存在，已跳过向量索引；资料已保存，可用于原文检索和离线 RAG 检索。"
    if detail == "文档内容提取或向量化失败":
        return "向量模型没有返回可用结果，请检查向量模型配置；资料已保存，可用于原文检索。"
    return detail


def _should_skip_vector_index(message: str) -> bool:
    detail = str(message or "")
    lower_detail = detail.lower()
    return (
        "error code: 404" in lower_detail
        or "model_not_found" in lower_detail
        or "model not found" in lower_detail
        or "向量模型调用失败" in detail
        or "未配置向量模型" in detail
    )


async def ingest_knowledge_document(kb_manager_or_upload_file, upload_file=None, *, index_now: bool = True) -> str:
    if upload_file is None:
        kb_manager = _resolve_kb_manager(materialize=False) if index_now else _KnowledgeUploadStorage()
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
        if not index_now:
            message = "资料已保存；向量索引未同步执行，可在资料列表中重建索引。"
            _update_vault_record(safe_filename, vector_status="pending", vector_error=message)
            return f"已保存到资料库（RAG 知识库）；{message}"
        timeout_seconds = _knowledge_reindex_timeout_seconds()
        setup_timeout_seconds = _knowledge_setup_timeout_seconds(timeout_seconds)
        try:
            embedding_config = await asyncio.wait_for(
                asyncio.to_thread(_resolve_knowledge_embedding_client_and_model),
                timeout=setup_timeout_seconds,
            )
        except asyncio.TimeoutError:
            detail = (
                f"向量模型初始化超过 {setup_timeout_seconds:g} 秒仍未完成，已中止；"
                "资料已保存，可稍后重建。"
            )
            _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
            return f"已保存到资料库（RAG 知识库）；RAG 检索索引未完成：{detail}"
        if embedding_config is None:
            message = "未配置向量模型，已跳过 RAG 索引；资料已保存，可用于原文检索。"
            _update_vault_record(safe_filename, vector_status="skipped", vector_error=message)
            return f"已保存到资料库（RAG 知识库）；{message}"
        client, embedding_model = embedding_config
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    _run_knowledge_ingest_blocking,
                    kb_manager,
                    file_path,
                    client,
                    embedding_model,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            detail = (
                f"向量索引超过 {timeout_seconds:g} 秒仍未完成，已中止；"
                "资料已保存，可稍后重建。"
            )
            _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
            return f"已保存到资料库（RAG 知识库）；RAG 检索索引未完成：{detail}"
    except KnowledgeBaseServiceError:
        raise
    except Exception as exc:
        detail = _friendly_vector_message(str(exc))
        if "vault_record" in locals():
            _update_vault_record(safe_filename, vector_status="skipped", vector_error=detail)
            return f"已保存到资料库（RAG 知识库）；RAG 索引跳过：{detail}"
        raise KnowledgeBaseServiceError(500, detail) from exc

    if result.get("status") == "success":
        _update_vault_record(safe_filename, vector_status="indexed")
        return str(result.get("message") or "")
    raw_message = str(result.get("message") or "文档内容提取或向量化失败")
    message = _friendly_vector_message(raw_message)
    if _should_skip_vector_index(raw_message):
        _update_vault_record(safe_filename, vector_status="skipped", vector_error=message)
        return f"已保存到资料库（RAG 知识库）；RAG 索引跳过：{message}"
    _update_vault_record(safe_filename, vector_status="failed", vector_error=message)
    return f"已保存到资料库（RAG 知识库）；RAG 检索索引未完成：{message}"


async def list_knowledge_document_records(kb_manager=None) -> list[Any]:
    vault_records = []
    for item in list_vault_source_records():
        if isinstance(item, dict) and item.get("vector_error"):
            raw_error = str(item.get("vector_error") or "")
            item = {**item, "vector_error": _friendly_vector_message(raw_error)}
            if item.get("vector_status") == "failed" and _should_skip_vector_index(raw_error):
                item["vector_status"] = "skipped"
        vault_records.append(item)
    if vault_records:
        return vault_records

    kb_manager = _resolve_kb_manager(kb_manager)
    try:
        kb_records = await kb_manager.list_documents()
    except Exception as exc:
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    merged: dict[str, Any] = {}
    for item in kb_records:
        if isinstance(item, dict):
            filename = str(item.get("filename") or item.get("name") or "")
            if filename:
                merged[filename] = item
        else:
            filename = str(item)
            merged.setdefault(filename, {"filename": filename, "status": "legacy_vector"})
    return list(merged.values())


def _document_timestamp(record: dict[str, Any]) -> str:
    return str(record.get("updated_at") or record.get("created_at") or "")


def _record_text(record: dict[str, Any]) -> str:
    values = [
        record.get("filename"),
        record.get("original_filename"),
        record.get("source_path"),
        record.get("note_path"),
        record.get("compile_status"),
        record.get("vector_status"),
        " ".join(str(tag) for tag in record.get("tags") or []),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _count_by(records: list[dict[str, Any]], key: str, default: str = "unknown") -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key) or default)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _knowledge_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_size = 0
    for record in records:
        try:
            total_size += int(record.get("size") or 0)
        except (TypeError, ValueError):
            pass
    vector_counts = _count_by(records, "vector_status", "unknown")
    indexed = vector_counts.get("indexed", 0)
    searchable = indexed + vector_counts.get("skipped", 0)
    return {
        "total": len(records),
        "total_size": total_size,
        "vector_counts": vector_counts,
        "compile_counts": _count_by(records, "compile_status", "unknown"),
        "extension_counts": _count_by(records, "extension", "unknown"),
        "searchable_count": searchable,
        "indexed_ratio": round(indexed / len(records), 4) if records else 0,
        "latest_updated_at": max((_document_timestamp(record) for record in records), default=""),
    }


def _sort_knowledge_records(records: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "name_asc":
        return sorted(records, key=lambda item: str(item.get("original_filename") or item.get("filename") or "").lower())
    if sort == "name_desc":
        return sorted(records, key=lambda item: str(item.get("original_filename") or item.get("filename") or "").lower(), reverse=True)
    if sort == "size_desc":
        return sorted(records, key=lambda item: int(item.get("size") or 0), reverse=True)
    if sort == "size_asc":
        return sorted(records, key=lambda item: int(item.get("size") or 0))
    if sort == "created_desc":
        return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return sorted(records, key=_document_timestamp, reverse=True)


def get_knowledge_vector_store_status(kb_manager=None, *, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    from core.embedding_config import get_embedding_config
    from core.knowledge_vector_config import knowledge_vector_table_name

    embedding_model, embedding_dim = get_embedding_config()
    db_path = str(getattr(kb_manager, "db_path", "") or os.getenv("OPSCORE_LANCEDB_PATH") or "opscore_lancedb")
    db_path_exists = Path(db_path).exists()
    table_exists = db_path_exists
    table_name = knowledge_vector_table_name(embedding_dim)
    vector_counts = dict((summary or {}).get("vector_counts") or {})
    indexed_count = int(vector_counts.get("indexed") or 0)
    skipped_count = int(vector_counts.get("skipped") or 0)
    failed_count = int(vector_counts.get("failed") or 0)
    pending_count = int(vector_counts.get("pending") or 0)
    diagnostics = [
        "资料列表只读取文件清单和状态，不扫描 LanceDB 大表。",
        "点击单篇资料的重建向量时，才会连接向量库并调用向量模型。",
    ]

    if not embedding_model:
        status = "missing_embedding_model"
        status_label = "缺少向量模型"
        health = "needs_model"
        message = "未配置向量化模型，资料会保存原文，但不会写入向量库。"
        action_label = "配置向量模型"
        recommended_action = "到模型配置里选择可用的 Embedding/向量化模型，然后回到资料列表重建向量。"
    elif failed_count > 0:
        status = "needs_attention"
        status_label = "部分资料索引失败"
        health = "warning"
        message = f"当前有 {failed_count} 份资料向量索引失败，原文仍可查看；请先查看失败原因，再按需重建。"
        action_label = "查看失败并重建"
        recommended_action = "在资料列表筛选“失败”，查看每份资料的 RAG 提示；确认模型和 LanceDB 正常后逐个重建。"
    elif not table_exists:
        status = "empty"
        status_label = "向量库未创建"
        health = "empty"
        message = "LanceDB 目录尚未创建，上传并成功向量化后会自动创建。"
        action_label = "上传资料"
        recommended_action = "先上传资料；如果已上传但没有向量，请确认向量模型可用后重建。"
    elif indexed_count > 0:
        status = "ready"
        status_label = "RAG 可用"
        health = "ok"
        message = f"已有 {indexed_count} 份资料完成向量化，可参与 RAG 召回。"
        action_label = "继续维护"
        recommended_action = "继续上传资料，或使用搜索/筛选检查未向量化和失败资料。"
    else:
        status = "configured"
        status_label = "向量库已配置"
        health = "configured"
        message = "LanceDB 目录存在；资料列表不会整表扫描向量库，避免大量资料时阻塞页面。"
        action_label = "重建向量"
        recommended_action = "选择需要参与 RAG 的资料，点击“重建向量”。"

    return {
        "status": status,
        "status_label": status_label,
        "health": health,
        "message": message,
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "model_configured": bool(embedding_model),
        "database": "LanceDB",
        "db_path": db_path,
        "table": table_name,
        "table_exists": table_exists,
        "db_path_exists": db_path_exists,
        "table_names": [],
        "chunk_count": None,
        "source_count": None,
        "indexed_count": indexed_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
        "reindex_timeout_seconds": _knowledge_reindex_timeout_seconds(),
        "action_label": action_label,
        "recommended_action": recommended_action,
        "diagnostics": diagnostics,
        "error": "",
    }


async def list_knowledge_document_page(
    kb_manager=None,
    *,
    query: str = "",
    vector_status: str = "all",
    extension: str = "all",
    page: int = 1,
    per_page: int = 50,
    sort: str = "updated_desc",
) -> dict[str, Any]:
    raw_records = await list_knowledge_document_records(kb_manager)
    records = [record if isinstance(record, dict) else {"filename": str(record), "status": "legacy_vector"} for record in raw_records]
    summary = _knowledge_summary(records)
    query_text = str(query or "").strip().lower()
    filtered = records
    if query_text:
        filtered = [record for record in filtered if query_text in _record_text(record)]
    if vector_status and vector_status != "all":
        filtered = [record for record in filtered if str(record.get("vector_status") or "unknown") == vector_status]
    if extension and extension != "all":
        normalized_ext = extension if extension.startswith(".") else f".{extension}"
        filtered = [record for record in filtered if str(record.get("extension") or Path(str(record.get("filename") or "")).suffix).lower() == normalized_ext.lower()]
    sorted_records = _sort_knowledge_records(filtered, sort)
    safe_per_page = max(10, min(int(per_page or 50), 200))
    safe_page = max(1, int(page or 1))
    total_filtered = len(sorted_records)
    page_count = max(1, math.ceil(total_filtered / safe_per_page)) if total_filtered else 1
    safe_page = min(safe_page, page_count)
    start = (safe_page - 1) * safe_per_page
    end = start + safe_per_page
    return {
        "files": sorted_records[start:end],
        "summary": {
            **summary,
            "filtered": total_filtered,
            "query": query,
            "active_vector_status": vector_status,
            "active_extension": extension,
        },
        "pagination": {
            "page": safe_page,
            "per_page": safe_per_page,
            "total": total_filtered,
            "page_count": page_count,
            "has_prev": safe_page > 1,
            "has_next": safe_page < page_count,
        },
        "vector_store": get_knowledge_vector_store_status(kb_manager, summary=summary),
    }


async def reindex_knowledge_document_record(
    identifier: str,
    kb_manager=None,
    *,
    vault_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    root, record = _find_vault_record(identifier, vault_dir)
    source_path = _resolve_vault_record_path(root, record.get("source_path"), "资料原文")
    safe_filename = str(record.get("filename") or source_path.name)
    embedding_config = _resolve_knowledge_embedding_client_and_model()
    if embedding_config is None:
        message = "未配置向量模型，无法重建向量索引；资料原文仍保留。"
        _update_vault_record(safe_filename, vector_status="skipped", vector_error=message)
        return {
            **record,
            "filename": safe_filename,
            "vector_status": "skipped",
            "vector_error": message,
            "message": message,
        }

    client, embedding_model = embedding_config
    timeout_seconds = _knowledge_reindex_timeout_seconds()
    if kb_manager is None:
        manager_timeout = _knowledge_setup_timeout_seconds(timeout_seconds)
        try:
            kb_manager = await asyncio.wait_for(
                asyncio.to_thread(_resolve_kb_manager, None),
                timeout=manager_timeout,
            )
        except asyncio.TimeoutError:
            detail = (
                f"向量库初始化超过 {manager_timeout:g} 秒仍未完成，已中止；"
                "请检查 LanceDB 目录、文件锁或稍后重试。"
            )
            _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
            return {
                **record,
                "filename": safe_filename,
                "vector_status": "failed",
                "vector_error": detail,
                "message": f"重建向量索引失败：{detail}",
            }
        except Exception as exc:
            detail = _friendly_vector_message(str(exc))
            _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
            return {
                **record,
                "filename": safe_filename,
                "vector_status": "failed",
                "vector_error": detail,
                "message": f"重建向量索引失败：{detail}",
            }
    else:
        kb_manager = _resolve_kb_manager(kb_manager)

    try:
        async def _run_reindex():
            try:
                await kb_manager.delete_document(safe_filename)
            except Exception:
                pass
            return await kb_manager.ingest_document(str(source_path), client, embedding_model)

        result = await asyncio.wait_for(_run_reindex(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        detail = (
            f"向量重建超过 {timeout_seconds:g} 秒仍未完成，已中止；"
            "请检查向量模型连通性、模型名称或稍后重试。"
        )
        _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
        return {
            **record,
            "filename": safe_filename,
            "vector_status": "failed",
            "vector_error": detail,
            "message": f"重建向量索引失败：{detail}",
        }
    except Exception as exc:
        detail = _friendly_vector_message(str(exc))
        _update_vault_record(safe_filename, vector_status="failed", vector_error=detail)
        return {
            **record,
            "filename": safe_filename,
            "vector_status": "failed",
            "vector_error": detail,
            "message": f"重建向量索引失败：{detail}",
        }

    raw_message = str(result.get("message") or "文档内容提取或向量化失败")
    if result.get("status") == "success":
        _update_vault_record(safe_filename, vector_status="indexed", vector_error="")
        updated_record = read_knowledge_document_record(safe_filename, vault_dir=root)
        return {
            **updated_record,
            "vector_status": "indexed",
            "vector_error": "",
            "message": raw_message or "资料向量索引已重建",
        }

    message = _friendly_vector_message(raw_message)
    next_status = "skipped" if _should_skip_vector_index(raw_message) else "failed"
    _update_vault_record(safe_filename, vector_status=next_status, vector_error=message)
    return {
        **record,
        "filename": safe_filename,
        "vector_status": next_status,
        "vector_error": message,
        "message": f"重建向量索引未完成：{message}",
    }


async def remove_knowledge_document_record(kb_manager_or_filename, filename: str | None = None) -> str:
    if filename is None:
        kb_manager = _KnowledgeUploadStorage()
        filename = str(kb_manager_or_filename)
    else:
        kb_manager = _resolve_kb_manager(kb_manager_or_filename)

    try:
        result = await kb_manager.delete_document(filename)
    except Exception as exc:
        removed_from_vault = remove_vault_source_record(filename)
        removed_legacy_copy = remove_legacy_knowledge_upload_copy(kb_manager, filename)
        if removed_from_vault:
            return f"已从资料库移除 {filename}"
        if removed_legacy_copy:
            return f"已从兼容目录移除 {filename}"
        if isinstance(kb_manager, _KnowledgeUploadStorage):
            raise KnowledgeBaseServiceError(404, "知识库文档不存在") from exc
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    removed_from_vault = remove_vault_source_record(filename)
    remove_legacy_knowledge_upload_copy(kb_manager, filename)
    if result.get("status") == "success":
        return str(result.get("message") or "")
    if removed_from_vault:
        return f"已从资料库移除 {filename}"
    raise KnowledgeBaseServiceError(404, str(result.get("message") or "知识库文档不存在"))
