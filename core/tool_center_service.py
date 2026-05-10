from __future__ import annotations

from typing import Any

from core.hermes_tool_adapter import (
    HERMES_AGENT_EXCLUDED_TOOL_NAMES,
    iter_hermes_tool_metadata,
    load_error,
)
from core.tool_display import TOOL_LABELS, TOOLSET_LABELS


NOT_WIRED_HERMES_TOOLS = {"delegate_task", "session_search"}


def _toolset_payload(toolset: str) -> dict[str, Any]:
    return {
        "id": toolset,
        "label": TOOLSET_LABELS.get(toolset, toolset),
        "tools": [],
    }


def _status_label(status: str) -> str:
    return {
        "available": "当前可用",
        "controlled": "受控未启用",
        "not_wired": "未接入",
    }.get(status, status)


def _controlled_reason(name: str) -> str:
    if name in NOT_WIRED_HERMES_TOOLS:
        return "该 Hermes 能力还没有接入 OpsCore 会话、审批和审计链路。"
    return "该工具涉及本地写入、代码执行、进程、计划任务或平台外发，默认不暴露给模型。"


def _registered_tool_item(tool: Any) -> dict[str, Any]:
    item = tool.public_dict()
    item.update(
        {
            "status": "available",
            "status_label": _status_label("available"),
            "model_exposed": True,
            "execution_enabled": True,
            "source": "opscore",
            "control_reason": "",
        }
    )
    return item


def _controlled_hermes_tool_items(registered_names: set[str]) -> list[dict[str, Any]]:
    load_problem = load_error()
    metadata = {item["name"]: item for item in iter_hermes_tool_metadata(HERMES_AGENT_EXCLUDED_TOOL_NAMES)}
    items: list[dict[str, Any]] = []

    for name in sorted(HERMES_AGENT_EXCLUDED_TOOL_NAMES):
        if name in registered_names:
            continue
        item = metadata.get(name)
        schema = item.get("schema", {}) if item else {}
        toolset = f"hermes-{item['toolset']}" if item else "hermes-controlled"
        status = "not_wired" if name in NOT_WIRED_HERMES_TOOLS or item is None else "controlled"
        reason = _controlled_reason(name)
        if item is None and load_problem:
            reason = f"Hermes 工具元数据加载失败：{load_problem}"

        items.append(
            {
                "name": name,
                "label": TOOL_LABELS.get(name, name),
                "toolset": toolset,
                "scope": "base",
                "description": str(schema.get("description") or ""),
                "safety_category": "local_write" if name in {"write_file", "patch", "skill_manage"} else "local_execute",
                "protocols": [],
                "asset_types": [],
                "requires_virtual": False,
                "enabled": False,
                "status": status,
                "status_label": _status_label(status),
                "model_exposed": False,
                "execution_enabled": False,
                "source": "hermes",
                "control_reason": reason,
            }
        )
    return items


def build_tool_center_catalog(tool_registry: Any) -> dict[str, Any]:
    registered_tools = tool_registry.all_tools()
    registered_names = {tool.name for tool in registered_tools}
    toolsets: dict[str, dict[str, Any]] = {}

    for tool in registered_tools:
        bucket = toolsets.setdefault(tool.toolset, _toolset_payload(tool.toolset))
        bucket["tools"].append(_registered_tool_item(tool))

    for item in _controlled_hermes_tool_items(registered_names):
        bucket = toolsets.setdefault(item["toolset"], _toolset_payload(item["toolset"]))
        bucket["tools"].append(item)

    ordered_toolsets = sorted(toolsets.values(), key=lambda entry: str(entry["label"]))
    for toolset in ordered_toolsets:
        toolset["tools"] = sorted(toolset["tools"], key=lambda entry: str(entry["label"]))
        counts = {"available": 0, "controlled": 0, "not_wired": 0}
        for tool in toolset["tools"]:
            status = str(tool.get("status") or "available")
            counts[status] = counts.get(status, 0) + 1
        toolset["counts"] = counts

    summary = {"total": 0, "available": 0, "controlled": 0, "not_wired": 0}
    for toolset in ordered_toolsets:
        for status, count in toolset["counts"].items():
            summary[status] = summary.get(status, 0) + int(count)
            summary["total"] += int(count)

    return {
        "summary": summary,
        "toolsets": ordered_toolsets,
        "status_labels": {
            "available": _status_label("available"),
            "controlled": _status_label("controlled"),
            "not_wired": _status_label("not_wired"),
        },
    }
