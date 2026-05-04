from pydantic import BaseModel, Field
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.errors import raise_http_error
from api.response_mappers.knowledge import (
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
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
    memory_stores_response_kwargs,
    memory_versions_response_kwargs,
)
from api.schema_models.common import ResponseModel
from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    ingest_knowledge_document,
    list_knowledge_document_records,
    remove_knowledge_document_record,
)


router = APIRouter()


class MemoryUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    content_sha256: str | None = None


class MemoryRestoreRequest(BaseModel):
    version_id: str = Field(..., min_length=1)


class MemoryConflictResolveRequest(BaseModel):
    version_id: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(accept_new|keep_old|merged)$")


class MemoryReviewConfirmRequest(BaseModel):
    path: str = Field(..., min_length=1)


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


@router.delete("/knowledge/{filename}", response_model=ResponseModel)
async def delete_knowledge_document(filename: str):
    """【新功能】从知识库中删除某个文档"""
    try:
        message = await remove_knowledge_document_record(filename)
    except KnowledgeBaseServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**knowledge_document_deleted_response_kwargs(message))
