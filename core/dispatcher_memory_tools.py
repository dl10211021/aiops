"""Governed memory tool execution for AI-managed session memory."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.file_memory_store import memory_scope_path


MEMORY_TOOL_NAMES = {
    "memory_list",
    "memory_read",
    "memory_write",
    "memory_edit",
    "memory_delete",
}


async def execute_memory_tool(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    try:
        return await asyncio.to_thread(_execute_memory_tool_sync, tool_call_name, args, context, log)
    except Exception as exc:
        log.exception("memory tool failed: %s", tool_call_name)
        return json.dumps(
            {
                "status": "ERROR",
                "error": str(exc),
                "tool": tool_call_name,
            },
            ensure_ascii=False,
        )


def _execute_memory_tool_sync(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    logger: logging.Logger,
) -> str:
    from core.memory import memory_db

    store = memory_db.file_memory_store
    session_id = str(context.get("session_id") or "")

    if tool_call_name == "memory_list":
        query = str(args.get("query") or "").strip()
        limit = _safe_limit(args.get("limit"), default=10, maximum=50)
        scope_ids = _context_scope_ids(context)
        if query:
            results = store.search(scope_ids=scope_ids, query=query, limit=limit)
            for result in results:
                scope_id = result.get("_memory_scope_id")
                if scope_id and not result.get("_memory_path"):
                    result["_memory_path"] = memory_scope_path(str(scope_id)).as_posix()
            return _json({"status": "SUCCESS", "scope_ids": scope_ids, "results": results})
        items = _filter_context_memories(store.list_memories(), scope_ids)[:limit]
        return _json({"status": "SUCCESS", "scope_ids": scope_ids, "memories": items})

    if tool_call_name == "memory_read":
        path = _required(args, "path")
        detail = store.read_memory(path)
        return _json({"status": "SUCCESS", "memory": detail})

    if tool_call_name == "memory_write":
        content = _required(args, "content")
        scope = str(args.get("scope") or "current_session")
        scope_id = _resolve_write_scope(scope, context)
        version = store.append_memory(
            scope_id=scope_id,
            summary=content,
            source_session_id=session_id or None,
            metadata={
                "source": "agent_memory_tool",
                "tool": "memory_write",
                "actor": "ai",
                "scope": scope,
            },
        )
        logger.info("AI wrote memory scope=%s path=%s", scope_id, version.get("path"))
        return _json({"status": "SUCCESS", "version": version})

    if tool_call_name == "memory_edit":
        path = _required(args, "path")
        content = _required(args, "content")
        content_sha256 = str(args.get("content_sha256") or "").strip() or None
        version = store.update_memory(
            path,
            content=content,
            content_sha256=content_sha256,
            actor="agent_memory_tool",
        )
        logger.info("AI edited memory path=%s", path)
        return _json({"status": "SUCCESS", "version": version})

    if tool_call_name == "memory_delete":
        path = _required(args, "path")
        version = store.delete_memory(path, actor="agent_memory_tool")
        logger.info("AI deleted memory path=%s", path)
        return _json({"status": "SUCCESS", "version": version})

    return _json({"status": "ERROR", "error": "Unknown memory tool"})


def _context_scope_ids(context: dict[str, Any]) -> list[str]:
    scope_ids: list[str] = []
    session_id = str(context.get("session_id") or "").strip()
    if session_id:
        scope_ids.append(session_id)
    for scope_id in context.get("memory_scope_ids") or []:
        _append_unique(scope_ids, str(scope_id))

    host = str(context.get("host") or "").strip()
    if host:
        _append_unique(scope_ids, f"asset-host:{host}")
        protocol = str(context.get("protocol") or "").strip()
        port = str(context.get("port") or "").strip()
        if protocol and port:
            _append_unique(scope_ids, f"asset:{protocol}:{host}:{port}")

    asset_type = str(context.get("asset_type") or "").strip()
    if asset_type:
        _append_unique(scope_ids, f"asset-kind:{asset_type}")
    return scope_ids


def _filter_context_memories(items: list[dict[str, Any]], scope_ids: list[str]) -> list[dict[str, Any]]:
    if not scope_ids:
        return items
    allowed_paths = {memory_scope_path(scope_id).as_posix() for scope_id in scope_ids}
    return [item for item in items if item.get("path") in allowed_paths]


def _resolve_write_scope(scope: str, context: dict[str, Any]) -> str:
    if scope == "current_session":
        session_id = str(context.get("session_id") or "").strip()
        if not session_id:
            raise ValueError("current_session scope requires session_id")
        return session_id
    if scope == "current_host":
        host = str(context.get("host") or "").strip()
        if not host:
            raise ValueError("current_host scope requires host")
        return f"asset-host:{host}"
    if scope == "current_asset":
        protocol = str(context.get("protocol") or "").strip()
        host = str(context.get("host") or "").strip()
        port = str(context.get("port") or "").strip()
        if not protocol or not host or not port:
            raise ValueError("current_asset scope requires protocol, host and port")
        return f"asset:{protocol}:{host}:{port}"
    if scope == "asset_kind":
        asset_type = str(context.get("asset_type") or "").strip()
        if not asset_type:
            raise ValueError("asset_kind scope requires asset_type")
        return f"asset-kind:{asset_type}"
    raise ValueError(f"unsupported memory scope: {scope}")


def _safe_limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(1, min(parsed, maximum))


def _required(args: dict[str, Any], key: str) -> str:
    value = str(args.get(key) or "").strip()
    if not value:
        raise ValueError(f"missing required argument: {key}")
    return value


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
