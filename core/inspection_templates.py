"""CRUD storage and validation for read-only inspection templates."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from core.inspection_template_catalog import (
    ALLOWED_TOOLS,
    BUILTIN_TEMPLATES,
    WINDOWS_SECURITY_AUDIT_COMMAND,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_STORE_PATH = ROOT_DIR / "inspection_templates.json"

_LOCK = threading.RLock()

UNSAFE_PATTERNS = [
    r"\brm\s+",
    r"\bdel\s+",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\btruncate\b",
    r"\binsert\b",
    r"\bupdate\b",
    r"\breplace\b",
    r"\brestart\b",
    r"\bstop\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\b",
    r"\bsystemctl\s+(restart|stop|disable|mask)",
    r"\bdocker\s+(rm|rmi|stop|restart|exec|cp)",
    r"\bkubectl\s+(delete|apply|create|replace|patch|scale)",
]


def _read_store() -> list[dict[str, Any]]:
    if not TEMPLATE_STORE_PATH.exists():
        return []
    try:
        data = json.loads(TEMPLATE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _write_store(items: list[dict[str, Any]]) -> None:
    TEMPLATE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clean_id(value: object) -> str:
    raw = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("-")


def _assert_safe_text(value: object, field_name: str) -> None:
    text = str(value or "").strip().lower()
    if not text:
        return
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(f"{field_name} 包含非只读或高风险片段: {pattern}")


def normalize_template(template: dict[str, Any]) -> dict[str, Any]:
    template_id = _clean_id(template.get("id") or template.get("name"))
    if not template_id:
        raise ValueError("巡检模板 id 不能为空")

    steps = template.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("巡检模板至少需要一个 step")

    normalized_steps = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step #{index} 必须是对象")
        tool = str(step.get("tool") or "").strip()
        if tool not in ALLOWED_TOOLS:
            raise ValueError(f"step #{index} 使用了不支持的工具: {tool}")

        method = str(step.get("method") or "GET").upper()
        if method not in {"GET", "HEAD"}:
            raise ValueError("巡检模板只允许 GET/HEAD 类只读 HTTP 方法")

        _assert_safe_text(step.get("command"), "command")
        _assert_safe_text(step.get("sql"), "sql")
        _assert_safe_text(step.get("path"), "path")
        _assert_safe_text(step.get("operation"), "operation")
        _assert_safe_text(step.get("bucket"), "bucket")
        _assert_safe_text(step.get("prefix"), "prefix")
        _assert_safe_text(step.get("key"), "key")

        normalized_steps.append(
            {
                "name": _clean_id(step.get("name") or f"step-{index}"),
                "title": str(step.get("title") or step.get("name") or f"Step {index}").strip(),
                "tool": tool,
                "command": str(step.get("command") or "").strip(),
                "sql": str(step.get("sql") or "").strip(),
                "path": str(step.get("path") or "").strip(),
                "oid": str(step.get("oid") or "").strip(),
                "operation": str(step.get("operation") or "").strip(),
                "bucket": str(step.get("bucket") or "").strip(),
                "prefix": str(step.get("prefix") or "").strip(),
                "key": str(step.get("key") or "").strip(),
                "max_keys": int(step.get("max_keys") or 0),
                "method": method,
                "timeout": int(step.get("timeout") or 15),
                "args": step.get("args") if isinstance(step.get("args"), dict) else {},
            }
        )

    is_builtin = bool(template.get("builtin"))
    source = "builtin" if is_builtin else str(template.get("source") or "custom").strip() or "custom"

    asset_types = template.get("asset_types")
    if isinstance(asset_types, list):
        normalized_asset_types = [
            item
            for item in (str(value or "").strip().lower() for value in asset_types)
            if item
        ]
    else:
        normalized_asset_types = []
    asset_type = str(template.get("asset_type") or "*").strip().lower()
    if not normalized_asset_types:
        normalized_asset_types = [asset_type]

    return {
        "id": template_id,
        "name": str(template.get("name") or template_id).strip(),
        "asset_type": asset_type,
        "asset_types": normalized_asset_types,
        "protocol": str(template.get("protocol") or "*").strip().lower(),
        "enabled": bool(template.get("enabled", True)),
        "builtin": is_builtin,
        "readonly": bool(template.get("readonly", is_builtin)),
        "source": source,
        "steps": normalized_steps,
    }


def _builtin_template_ids() -> set[str]:
    return {_clean_id(item.get("id")) for item in BUILTIN_TEMPLATES}


def _normalize_builtin_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    templates = [normalize_template({**item, "builtin": True, "readonly": True}) for item in BUILTIN_TEMPLATES]
    if include_disabled:
        return templates
    return [item for item in templates if item.get("enabled")]


def _normalize_custom_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    templates = [
        {
            **normalize_template(item),
            "builtin": False,
            "readonly": bool(item.get("readonly", True)),
            "source": "custom",
        }
        for item in _read_store()
    ]
    if include_disabled:
        return templates
    return [item for item in templates if item.get("enabled")]


def list_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    with _LOCK:
        builtins = _normalize_builtin_templates(include_disabled=include_disabled)
        custom = _normalize_custom_templates(include_disabled=include_disabled)
    return [*builtins, *custom]


def save_template(template: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_template(template)
    if normalized["id"] in _builtin_template_ids():
        raise ValueError("内置巡检模板为只读，不能覆盖")
    normalized["builtin"] = False
    normalized["readonly"] = bool(template.get("readonly", True))
    normalized["source"] = "custom"
    with _LOCK:
        items = _read_store()
        next_items = [item for item in items if _clean_id(item.get("id")) != normalized["id"]]
        next_items.append(normalized)
        _write_store(sorted(next_items, key=lambda item: item["id"]))
    return normalized


def delete_template(template_id: str) -> bool:
    clean = _clean_id(template_id)
    if clean in _builtin_template_ids():
        return False
    with _LOCK:
        items = _read_store()
        next_items = [item for item in items if _clean_id(item.get("id")) != clean]
        if len(next_items) == len(items):
            return False
        _write_store(next_items)
    return True


def find_matching_template(asset_type: str, protocol: str) -> dict[str, Any] | None:
    asset_type = str(asset_type or "").lower()
    protocol = str(protocol or "").lower()
    with _LOCK:
        templates = [
            *_normalize_custom_templates(include_disabled=False),
            *_normalize_builtin_templates(include_disabled=False),
        ]
    for template in templates:
        template_asset_types = set(template.get("asset_types") or [template.get("asset_type")])
        type_match = "*" in template_asset_types or asset_type in template_asset_types
        protocol_match = template["protocol"] in {"*", protocol}
        if type_match and protocol_match:
            return template
    return None
