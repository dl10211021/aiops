from pydantic import BaseModel, Field
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.errors import raise_http_error
from api.response_mappers.knowledge import (
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
    knowledge_vault_candidate_approved_response_kwargs,
    knowledge_vault_candidate_item_response_kwargs,
    knowledge_vault_candidate_response_kwargs,
    knowledge_vault_candidate_updated_response_kwargs,
    knowledge_vault_candidates_response_kwargs,
    knowledge_vault_article_item_response_kwargs,
    knowledge_vault_articles_response_kwargs,
    knowledge_vault_queue_response_kwargs,
    memory_item_created_response_kwargs,
    memory_item_deleted_response_kwargs,
    memory_export_response_kwargs,
    memory_item_response_kwargs,
    memory_item_restored_response_kwargs,
    memory_item_updated_response_kwargs,
    memory_items_response_kwargs,
    memory_pending_conflict_resolved_response_kwargs,
    memory_pending_conflicts_response_kwargs,
    memory_review_confirmed_response_kwargs,
    memory_review_items_response_kwargs,
    memory_search_response_kwargs,
    memory_stores_response_kwargs,
    memory_version_redacted_response_kwargs,
    memory_versions_response_kwargs,
)
from api.schema_models.common import ResponseModel
from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    approve_vault_candidate,
    compile_vault_source_candidate,
    ingest_knowledge_document,
    list_knowledge_document_records,
    list_vault_articles,
    list_vault_candidates,
    list_vault_compile_queue,
    read_vault_article,
    read_vault_candidate,
    remove_knowledge_document_record,
    update_vault_candidate,
)


router = APIRouter()


class MemoryUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_sha256: str | None = None


class MemoryCreateRequest(BaseModel):
    scope_id: str = Field(..., min_length=1, max_length=160)
    summary: str = Field(..., min_length=1, max_length=8000)
    source_session_id: str = Field("manual", max_length=160)


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    scope_ids: list[str] = Field(default_factory=lambda: ["manual"])
    limit: int = Field(6, ge=1, le=20)


class MemoryRestoreRequest(BaseModel):
    version_id: str = Field(..., min_length=1)


class MemoryVersionRedactRequest(BaseModel):
    version_id: str = Field(..., min_length=1)


class MemoryConflictResolveRequest(BaseModel):
    version_id: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(accept_new|keep_old|merged)$")


class MemoryReviewConfirmRequest(BaseModel):
    path: str = Field(..., min_length=1)


class KnowledgeVaultCompileRequest(BaseModel):
    source_session_id: str = Field(..., min_length=1, max_length=200)
    use_ai: bool = True


class KnowledgeVaultApproveRequest(BaseModel):
    source_session_id: str = Field(..., min_length=1, max_length=200)


class KnowledgeVaultCandidateUpdateRequest(BaseModel):
    source_session_id: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    content_sha256: str | None = None


@router.get("/knowledge/memory/stores", response_model=ResponseModel)
async def list_memory_stores():
    from core.memory import memory_db

    stores = memory_db.file_memory_store.list_stores()
    return ResponseModel(**memory_stores_response_kwargs(stores))


@router.get("/knowledge/memory/list", response_model=ResponseModel)
async def list_memory_items():
    from core.memory import memory_db

    items = memory_db.file_memory_store.list_memories()
    return ResponseModel(**memory_items_response_kwargs(items))


@router.get("/knowledge/memory/read", response_model=ResponseModel)
async def read_memory_item(path: str = Query(..., min_length=1)):
    from core.memory import memory_db

    try:
        item = memory_db.file_memory_store.read_memory(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="记忆路径非法")
    return ResponseModel(**memory_item_response_kwargs(item))


@router.post("/knowledge/memory/search", response_model=ResponseModel)
async def search_memory_items(req: MemorySearchRequest):
    from core.memory import memory_db

    scope_ids = [str(scope).strip() for scope in req.scope_ids if str(scope).strip()]
    if not scope_ids:
        raise HTTPException(status_code=400, detail="至少需要一个记忆作用域")
    results = memory_db.file_memory_store.search(
        scope_ids=scope_ids,
        query=req.query,
        limit=req.limit,
    )
    return ResponseModel(**memory_search_response_kwargs(results))


@router.post("/knowledge/memory", response_model=ResponseModel)
async def create_memory_item(req: MemoryCreateRequest):
    from core.memory import memory_db

    try:
        version = memory_db.file_memory_store.append_memory(
            scope_id=req.scope_id,
            summary=req.summary,
            source_session_id=req.source_session_id or "manual",
            metadata={"source": "manual_memory_create"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "记忆内容不能为空")
    return ResponseModel(**memory_item_created_response_kwargs(version))


@router.delete("/knowledge/memory", response_model=ResponseModel)
async def delete_memory_item(path: str = Query(..., min_length=1)):
    from core.memory import memory_db

    try:
        memory_db.file_memory_store.delete_memory(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="记忆路径非法")
    return ResponseModel(**memory_item_deleted_response_kwargs(path))


@router.get("/knowledge/memory/versions", response_model=ResponseModel)
async def list_memory_versions(limit: int = Query(50, ge=1, le=200)):
    from core.memory import memory_db

    versions = memory_db.file_memory_store.list_versions(limit=limit)
    return ResponseModel(**memory_versions_response_kwargs(versions))


@router.get("/knowledge/memory/pending", response_model=ResponseModel)
async def list_memory_pending_conflicts(limit: int = Query(50, ge=1, le=200)):
    from core.memory import memory_db

    items = memory_db.list_pending_memory_conflicts(limit=limit)
    return ResponseModel(**memory_pending_conflicts_response_kwargs(items))


@router.get("/knowledge/memory/review", response_model=ResponseModel)
async def list_memory_review_items(
    stale_days: int = Query(180, ge=1, le=3650),
    limit: int = Query(50, ge=1, le=200),
):
    from core.memory import memory_db

    items = memory_db.list_memory_review_items(stale_days=stale_days, limit=limit)
    return ResponseModel(**memory_review_items_response_kwargs(items))


@router.put("/knowledge/memory", response_model=ResponseModel)
async def update_memory_item(req: MemoryUpdateRequest, path: str = Query(..., min_length=1)):
    from core.memory import memory_db

    try:
        memory_db.file_memory_store.update_memory(
            path,
            content=req.content,
            content_sha256=req.content_sha256,
        )
        item = memory_db.file_memory_store.read_memory(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="该记忆库为只读，不能修改")
    except RuntimeError:
        raise HTTPException(status_code=409, detail="记忆已被其他操作修改，请刷新后重试")
    except ValueError:
        raise HTTPException(status_code=400, detail="记忆路径非法")
    return ResponseModel(**memory_item_updated_response_kwargs(item))


@router.post("/knowledge/memory/pending/resolve", response_model=ResponseModel)
async def resolve_memory_pending_conflict(req: MemoryConflictResolveRequest):
    from core.memory import memory_db

    try:
        version = memory_db.resolve_pending_memory_conflict(req.version_id, req.action)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="待确认记忆不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="该记忆库为只读，不能处理")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "待确认记忆处理参数无效")
    return ResponseModel(**memory_pending_conflict_resolved_response_kwargs(version))


@router.post("/knowledge/memory/review/confirm", response_model=ResponseModel)
async def confirm_memory_review(req: MemoryReviewConfirmRequest):
    from core.memory import memory_db

    try:
        version = memory_db.mark_memory_reviewed(req.path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="该记忆库为只读，不能标记复核")
    except ValueError:
        raise HTTPException(status_code=400, detail="记忆路径非法")
    return ResponseModel(**memory_review_confirmed_response_kwargs(version))


@router.post("/knowledge/memory/restore", response_model=ResponseModel)
async def restore_memory_version(req: MemoryRestoreRequest):
    from core.memory import memory_db

    try:
        version = memory_db.file_memory_store.restore_version(req.version_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆版本不存在")
    except PermissionError:
        raise HTTPException(status_code=403, detail="该记忆库为只读，不能恢复")
    except ValueError:
        raise HTTPException(status_code=400, detail="该版本缺少可恢复内容")
    return ResponseModel(**memory_item_restored_response_kwargs(version))


@router.post("/knowledge/memory/versions/redact", response_model=ResponseModel)
async def redact_memory_version(req: MemoryVersionRedactRequest):
    from core.memory import memory_db

    try:
        version = memory_db.file_memory_store.redact_version(req.version_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="记忆版本不存在")
    except RuntimeError as exc:
        if str(exc) == "memory_version_is_current":
            raise HTTPException(status_code=409, detail="当前最新记忆版本不能直接脱敏，请先写入新版本或删除当前记忆")
        raise HTTPException(status_code=400, detail=str(exc) or "记忆版本脱敏失败")
    except ValueError:
        raise HTTPException(status_code=400, detail="记忆版本数据不完整")
    return ResponseModel(**memory_version_redacted_response_kwargs(version))


@router.get("/knowledge/memory/export", response_model=ResponseModel)
async def export_memory_store():
    from core.memory import memory_db

    export_payload = memory_db.file_memory_store.export_store()
    return ResponseModel(**memory_export_response_kwargs(export_payload))


@router.post("/knowledge/upload", response_model=ResponseModel)
async def upload_knowledge_document(file: UploadFile = File(...)):
    """【新功能】上传运维文档并注入 LanceDB 知识库"""
    try:
        message = await ingest_knowledge_document(file)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_document_uploaded_response_kwargs(message))


@router.get("/knowledge/list", response_model=ResponseModel)
async def list_knowledge_documents():
    """【新功能】列出已注入知识库的文档列表"""
    try:
        files = await list_knowledge_document_records()
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_documents_response_kwargs(files))


@router.get("/knowledge/vault/queue", response_model=ResponseModel)
async def list_knowledge_vault_queue():
    """列出 Obsidian/LLM Wiki Vault 中等待辅助模型编译的 source session。"""
    return ResponseModel(**knowledge_vault_queue_response_kwargs(list_vault_compile_queue()))


@router.post("/knowledge/vault/compile", response_model=ResponseModel)
async def compile_knowledge_vault_source(req: KnowledgeVaultCompileRequest):
    """把 source session 编译成待人工确认的候选 Wiki 页面。"""
    try:
        item = await compile_vault_source_candidate(
            req.source_session_id,
            use_ai=req.use_ai,
        )
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_vault_candidate_response_kwargs(item))


@router.get("/knowledge/vault/candidates", response_model=ResponseModel)
async def list_knowledge_vault_candidates():
    """列出等待人工确认或已批准的候选 Wiki 页面。"""
    return ResponseModel(**knowledge_vault_candidates_response_kwargs(list_vault_candidates()))


@router.get("/knowledge/vault/candidate", response_model=ResponseModel)
async def read_knowledge_vault_candidate(source_session_id: str = Query(..., min_length=1)):
    """读取候选 Wiki Markdown 正文，供人工审阅和修订。"""
    try:
        item = read_vault_candidate(source_session_id)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_vault_candidate_item_response_kwargs(item))


@router.put("/knowledge/vault/candidate", response_model=ResponseModel)
async def update_knowledge_vault_candidate(req: KnowledgeVaultCandidateUpdateRequest):
    """保存人工修订后的候选 Wiki Markdown。"""
    try:
        item = update_vault_candidate(
            req.source_session_id,
            content=req.content,
            content_sha256=req.content_sha256,
        )
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_vault_candidate_updated_response_kwargs(item))


@router.get("/knowledge/vault/articles", response_model=ResponseModel)
async def list_knowledge_vault_articles():
    """列出已批准入库的正式 Wiki 文章。"""
    return ResponseModel(**knowledge_vault_articles_response_kwargs(list_vault_articles()))


@router.get("/knowledge/vault/article", response_model=ResponseModel)
async def read_knowledge_vault_article(source_session_id: str = Query(..., min_length=1)):
    """读取正式 Wiki Markdown 正文。"""
    try:
        item = read_vault_article(source_session_id)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_vault_article_item_response_kwargs(item))


@router.post("/knowledge/vault/approve", response_model=ResponseModel)
async def approve_knowledge_vault_candidate(req: KnowledgeVaultApproveRequest):
    """批准候选 Wiki 页面，将其写入正式 wiki/articles。"""
    try:
        item = approve_vault_candidate(req.source_session_id)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_vault_candidate_approved_response_kwargs(item))


@router.delete("/knowledge/{filename}", response_model=ResponseModel)
async def delete_knowledge_document(filename: str):
    """【新功能】从知识库中删除某个文档"""
    try:
        message = await remove_knowledge_document_record(filename)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_document_deleted_response_kwargs(message))
