from fastapi import APIRouter, File, UploadFile

from api.errors import raise_http_error
from api.mappers import (
    knowledge_document_deleted_response_kwargs,
    knowledge_document_uploaded_response_kwargs,
    knowledge_documents_response_kwargs,
)
from api.schemas import ResponseModel
from core.knowledge_base_service import (
    KnowledgeBaseServiceError,
    ingest_knowledge_document,
    list_knowledge_document_records,
    remove_knowledge_document_record,
)


router = APIRouter()


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
