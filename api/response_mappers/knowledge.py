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


def memory_pending_conflicts_response_kwargs(items: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"items": items},
    }


def memory_pending_conflict_resolved_response_kwargs(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "待确认记忆已处理",
        "data": {"version": version},
    }


def memory_review_items_response_kwargs(items: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"items": items},
    }


def memory_review_confirmed_response_kwargs(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "记忆已标记为复核通过",
        "data": {"version": version},
    }


def memory_stores_response_kwargs(stores: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"stores": stores},
    }


def memory_item_updated_response_kwargs(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "记忆已更新",
        "data": {"item": item},
    }


def memory_item_restored_response_kwargs(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "记忆版本已恢复",
        "data": {"version": version},
    }


def memory_export_response_kwargs(export_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"export": export_payload},
    }


def memory_item_deleted_response_kwargs(path: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"记忆已删除: {path}",
    }
