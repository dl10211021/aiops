from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any


class KnowledgeBaseServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


ALLOWED_KNOWLEDGE_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx", ".log"}
MAX_KNOWLEDGE_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


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


async def ingest_knowledge_document(kb_manager, upload_file) -> str:
    from core.llm_factory import get_embedding_client_and_model

    safe_filename = safe_knowledge_filename(upload_file.filename)
    client, embedding_model = get_embedding_client_and_model()
    try:
        file_path = persist_knowledge_upload(upload_file, kb_manager.kb_dir, safe_filename)
        result = await kb_manager.ingest_document(file_path, client, embedding_model)
    except KnowledgeBaseServiceError:
        raise
    except Exception as exc:
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    if result.get("status") == "success":
        return str(result.get("message") or "")
    raise KnowledgeBaseServiceError(422, str(result.get("message") or "文档内容提取或向量化失败"))


async def list_knowledge_document_records(kb_manager) -> list[Any]:
    try:
        return await kb_manager.list_documents()
    except Exception as exc:
        raise KnowledgeBaseServiceError(500, str(exc)) from exc


async def remove_knowledge_document_record(kb_manager, filename: str) -> str:
    try:
        result = await kb_manager.delete_document(filename)
    except Exception as exc:
        raise KnowledgeBaseServiceError(500, str(exc)) from exc

    if result.get("status") == "success":
        return str(result.get("message") or "")
    raise KnowledgeBaseServiceError(404, str(result.get("message") or "知识库文档不存在"))
