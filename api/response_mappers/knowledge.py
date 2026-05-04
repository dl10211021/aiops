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


def memory_items_response_kwargs(items: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"items": items},
    }


def memory_item_response_kwargs(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"item": item},
    }


def memory_versions_response_kwargs(versions: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"versions": versions},
    }


def memory_item_deleted_response_kwargs(path: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"记忆已删除: {path}",
    }
