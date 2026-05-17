"""Adapter for reusing Hermes tool implementations inside OpsCore.

The Hermes source tree is kept under .research/hermes-agent and remains the
source of truth for these tool schemas and handlers.  OpsCore imports it
read-only and exposes a thin routing layer instead of copying each tool.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger(__name__)

HERMES_TOOL_NAMES: set[str] = {
    "browser_back",
    "browser_click",
    "browser_console",
    "browser_get_images",
    "browser_navigate",
    "browser_press",
    "browser_scroll",
    "browser_snapshot",
    "browser_type",
    "browser_vision",
    "clarify",
    "cronjob",
    "delegate_task",
    "execute_code",
    "image_gen",
    "memory",
    "patch",
    "process",
    "read_file",
    "search_files",
    "send_message",
    "session_search",
    "skill_manage",
    "skill_view",
    "skills_list",
    "text_to_speech",
    "todo",
    "vision_analyze",
    "web_search",
    "write_file",
}

# Tools in this set are still available to the adapter for explicit internal
# calls, but are not advertised to or dispatched from the agent loop. They need
# OpsCore-native approval and audit integration before model-initiated use.
HERMES_AGENT_EXCLUDED_TOOL_NAMES: set[str] = {
    "cronjob",
    "delegate_task",
    "execute_code",
    "memory",
    "patch",
    "process",
    "send_message",
    "skill_manage",
    "text_to_speech",
    "web_search",
    "write_file",
}

HERMES_AGENT_TOOL_NAMES: set[str] = HERMES_TOOL_NAMES - HERMES_AGENT_EXCLUDED_TOOL_NAMES

_HERMES_MODULES = (
    "tools.file_tools",
    "tools.web_tools",
    "tools.browser_tool",
    "tools.clarify_tool",
    "tools.cronjob_tools",
    "tools.delegate_tool",
    "tools.code_execution_tool",
    "tools.image_generation_tool",
    "tools.memory_tool",
    "tools.process_registry",
    "tools.send_message_tool",
    "tools.session_search_tool",
    "tools.skill_manager_tool",
    "tools.skills_tool",
    "tools.todo_tool",
    "tools.tts_tool",
    "tools.vision_tools",
)

HERMES_TOOL_ALIASES: dict[str, str] = {
    "image_gen": "image_generate",
}

_LOCK = threading.Lock()
_LOADED = False
_LOAD_ERROR: str | None = None
_TODO_STORES: dict[str, Any] = {}
_MEMORY_STORE: Any | None = None


def hermes_root() -> Path:
    return Path(__file__).resolve().parents[1] / ".research" / "hermes-agent"


def opscore_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _json_error(message: str, **extra: Any) -> str:
    payload = {"status": "ERROR", "error": message}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _resolve_repo_path(raw_path: str | None, *, for_write: bool = False) -> Path:
    root = opscore_root().resolve()
    value = str(raw_path or ".").strip() or "."
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Hermes file tools are scoped to the OpsCore repository root.") from exc
    if for_write:
        research_root = (root / ".research" / "hermes-agent").resolve()
        try:
            resolved.relative_to(research_root)
        except ValueError:
            pass
        else:
            raise PermissionError("Refusing to write under .research/hermes-agent from OpsCore tools.")
    return resolved


def _execute_file_tool(name: str, args: dict[str, Any]) -> str | None:
    if name == "read_file":
        path = _resolve_repo_path(args.get("path"))
        offset = max(1, int(args.get("offset") or 1))
        limit = max(1, min(int(args.get("limit") or 500), 2000))
        if not path.exists() or not path.is_file():
            return _json_error(f"File not found: {args.get('path')}", path=str(path))
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = data[offset - 1 : offset - 1 + limit]
        content = "\n".join(f"{idx}|{line}" for idx, line in enumerate(selected, start=offset))
        return json.dumps(
            {
                "status": "SUCCESS",
                "path": str(path),
                "content": content,
                "total_lines": len(data),
                "truncated": offset - 1 + limit < len(data),
                "file_size": path.stat().st_size,
            },
            ensure_ascii=False,
        )

    if name == "search_files":
        root = _resolve_repo_path(args.get("path") or ".")
        pattern = str(args.get("pattern") or "")
        target = str(args.get("target") or "content")
        limit = max(1, min(int(args.get("limit") or 50), 500))
        offset = max(0, int(args.get("offset") or 0))
        file_glob = str(args.get("file_glob") or "*")
        output_mode = str(args.get("output_mode") or "content")
        context_lines = max(0, min(int(args.get("context") or 0), 10))
        matches: list[dict[str, Any]] = []
        excluded = {".git", "node_modules", ".venv", "venv", "__pycache__"}
        if target == "files":
            roots = [root] if root.is_file() else root.rglob(pattern)
            for item in roots:
                if any(part in excluded for part in item.parts):
                    continue
                if item.exists():
                    matches.append({"path": str(item)})
                if len(matches) >= offset + limit:
                    break
            return json.dumps({"status": "SUCCESS", "total_count": len(matches), "results": matches[offset:offset + limit]}, ensure_ascii=False)

        regex = re.compile(pattern, re.IGNORECASE)
        files = [root] if root.is_file() else root.rglob(file_glob)
        for file_path in files:
            if not file_path.is_file() or any(part in excluded for part in file_path.parts):
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            file_hits = []
            for line_no, line in enumerate(lines, start=1):
                if regex.search(line):
                    if output_mode == "files_only":
                        matches.append({"path": str(file_path)})
                        break
                    if output_mode == "count":
                        file_hits.append(line_no)
                        continue
                    start = max(1, line_no - context_lines)
                    end = min(len(lines), line_no + context_lines)
                    matches.append(
                        {
                            "path": str(file_path),
                            "line": line_no,
                            "text": line,
                            "context": [
                                {"line": idx, "text": lines[idx - 1]}
                                for idx in range(start, end + 1)
                                if idx != line_no
                            ],
                        }
                    )
                if len(matches) >= offset + limit and output_mode != "count":
                    break
            if output_mode == "count" and file_hits:
                matches.append({"path": str(file_path), "count": len(file_hits)})
            if len(matches) >= offset + limit:
                break
        return json.dumps({"status": "SUCCESS", "total_count": len(matches), "results": matches[offset:offset + limit]}, ensure_ascii=False)

    if name == "write_file":
        path = _resolve_repo_path(args.get("path"), for_write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get("content") or "")
        path.write_text(content, encoding="utf-8")
        return json.dumps({"status": "SUCCESS", "path": str(path), "bytes": len(content.encode("utf-8"))}, ensure_ascii=False)

    if name == "patch":
        mode = str(args.get("mode") or "replace")
        if mode != "replace":
            return _json_error("Only patch mode='replace' is supported by the OpsCore Windows adapter.", tool=name)
        path = _resolve_repo_path(args.get("path"), for_write=True)
        old = str(args.get("old_string") or "")
        new = str(args.get("new_string") or "")
        if not old:
            return _json_error("old_string is required for patch replace mode.", tool=name)
        content = path.read_text(encoding="utf-8")
        count = content.count(old)
        if count == 0:
            return _json_error("old_string not found.", path=str(path))
        if count > 1 and not args.get("replace_all"):
            return _json_error("old_string is not unique; pass replace_all=true or add more context.", path=str(path), matches=count)
        updated = content.replace(old, new) if args.get("replace_all") else content.replace(old, new, 1)
        path.write_text(updated, encoding="utf-8")
        return json.dumps({"status": "SUCCESS", "path": str(path), "replacements": count if args.get("replace_all") else 1}, ensure_ascii=False)

    return None


def _ensure_loaded() -> bool:
    global _LOADED, _LOAD_ERROR
    with _LOCK:
        if _LOADED:
            return True
        root = hermes_root()
        if not root.exists():
            _LOAD_ERROR = f"Hermes source tree not found: {root}"
            return False
        root_text = str(root)
        if root_text not in sys.path:
            sys.path.insert(0, root_text)
        try:
            for module_name in _HERMES_MODULES:
                importlib.import_module(module_name)
        except Exception as exc:
            logger.exception("Failed to import Hermes tools from %s", root)
            _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
            return False
        _LOADED = True
        _LOAD_ERROR = None
        return True


def _registry():
    if not _ensure_loaded():
        return None
    from tools.registry import registry

    return registry


def _resolve_hermes_tool_name(name: str) -> str:
    return HERMES_TOOL_ALIASES.get(name, name)


def load_error() -> str | None:
    _ensure_loaded()
    return _LOAD_ERROR


def iter_hermes_tool_schemas(names: Iterable[str] = HERMES_AGENT_TOOL_NAMES) -> list[dict[str, Any]]:
    registry = _registry()
    if registry is None:
        return []
    schemas: list[dict[str, Any]] = []
    for name in sorted(set(names)):
        resolved_name = _resolve_hermes_tool_name(name)
        schema = registry.get_schema(resolved_name)
        if not schema:
            continue
        schemas.append({**schema, "name": name})
    return schemas


def iter_hermes_tool_metadata(names: Iterable[str] = HERMES_AGENT_TOOL_NAMES) -> list[dict[str, Any]]:
    registry = _registry()
    if registry is None:
        return []
    items: list[dict[str, Any]] = []
    for name in sorted(set(names)):
        resolved_name = _resolve_hermes_tool_name(name)
        schema = registry.get_schema(resolved_name)
        if not schema:
            continue
        items.append(
            {
                "name": name,
                "schema": {**schema, "name": name},
                "toolset": registry.get_toolset_for_tool(resolved_name) or "hermes",
            }
        )
    return items


def hermes_tool_available(name: str) -> tuple[bool, str]:
    registry = _registry()
    if registry is None:
        return False, _LOAD_ERROR or "Hermes tools are not loaded"
    resolved_name = _resolve_hermes_tool_name(name)
    entry = registry.get_entry(resolved_name)
    if not entry:
        return False, f"Hermes tool is not registered: {name}"
    if entry.check_fn:
        try:
            if not bool(entry.check_fn()):
                env = ", ".join(entry.requires_env or [])
                suffix = f" Required env: {env}" if env else ""
                return False, f"Hermes tool requirements are not satisfied.{suffix}"
        except Exception as exc:
            return False, f"Hermes tool requirement check failed: {type(exc).__name__}: {exc}"
    return True, ""


def _todo_store(session_id: str):
    from tools.todo_tool import TodoStore

    key = session_id or "default"
    store = _TODO_STORES.get(key)
    if store is None:
        store = TodoStore()
        _TODO_STORES[key] = store
    return store


def _memory_store():
    global _MEMORY_STORE
    if _MEMORY_STORE is None:
        from tools.memory_tool import MemoryStore

        store = MemoryStore()
        store.load_from_disk()
        _MEMORY_STORE = store
    return _MEMORY_STORE


def execute_hermes_tool(name: str, args: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    context = context or {}
    if name not in HERMES_TOOL_NAMES:
        return _json_error(f"Unsupported Hermes tool: {name}", tool=name)
    resolved_name = _resolve_hermes_tool_name(name)

    if resolved_name in {"read_file", "search_files", "write_file", "patch"}:
        try:
            file_result = _execute_file_tool(resolved_name, args)
            if file_result is not None:
                return file_result
        except Exception as exc:
            return _json_error(f"{type(exc).__name__}: {exc}", tool=name)

    registry = _registry()
    if registry is None:
        return _json_error(_LOAD_ERROR or "Hermes tools are not loaded", tool=name)

    ok, reason = hermes_tool_available(name)
    if not ok:
        return _json_error(reason, tool=name)

    task_id = str(context.get("session_id") or "opscore")
    kwargs: dict[str, Any] = {
        "task_id": task_id,
        "session_id": task_id,
        "enabled_tools": sorted(HERMES_TOOL_NAMES),
    }

    if resolved_name == "todo":
        kwargs["store"] = _todo_store(task_id)
    elif resolved_name == "memory":
        kwargs["store"] = _memory_store()
    elif resolved_name == "session_search":
        from core.session_search_service import search_session_records

        return json.dumps(search_session_records(args), ensure_ascii=False, default=str)
    elif resolved_name == "delegate_task":
        return _json_error("delegate_task requires a live Hermes parent agent; use OpsCore dispatch_sub_agents for asset-session delegation.", tool=name)
    elif resolved_name == "clarify":
        return _json_error("clarify is handled by OpsCore's interaction loop and should not be routed through the dispatcher.", tool=name)

    old_terminal_cwd = os.environ.get("TERMINAL_CWD")
    os.environ["TERMINAL_CWD"] = str(opscore_root())
    try:
        return registry.dispatch(resolved_name, args, **kwargs)
    finally:
        if old_terminal_cwd is None:
            os.environ.pop("TERMINAL_CWD", None)
        else:
            os.environ["TERMINAL_CWD"] = old_terminal_cwd
