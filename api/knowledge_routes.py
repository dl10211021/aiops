from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.errors import raise_http_error
from api.response_mappers.knowledge import (
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
    memory_item_deleted_response_kwargs,
    memory_item_response_kwargs,
    memory_items_response_kwargs,
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
