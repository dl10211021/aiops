from __future__ import annotations

from typing import Any


def knowledge_document_uploaded_response_kwargs(message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }


def knowledge_documents_response_kwargs(files: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"files": files},
    }


def knowledge_document_deleted_response_kwargs(message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }
