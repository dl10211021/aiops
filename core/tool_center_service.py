from __future__ import annotations

import re
from typing import Any

from core.hermes_tool_adapter import (
    HERMES_AGENT_EXCLUDED_TOOL_NAMES,
    iter_hermes_tool_metadata,
    load_error,
)
from core.tool_display import TOOL_LABELS, TOOLSET_LABELS
from core.tool_registry import tool_runtime_metadata


NOT_WIRED_HERMES_TOOLS = {"delegate_task", "session_search"}

BUILTIN_TOOL_DESCRIPTIONS: dict[str, str] = {
    "browser_back": "返回浏览器上一页。",
    "browser_click": "点击页面上的指定元素。",
    "browser_console": "查看浏览器控制台信息。",
    "browser_get_images": "获取当前页面图片列表。",
    "browser_navigate": "打开指定网页。",
    "browser_press": "向页面发送键盘按键。",
    "browser_scroll": "滚动当前页面。",
    "browser_snapshot": "读取当前页面文本结构。",
    "browser_type": "向页面输入框填写文本。",
    "browser_vision": "截图并分析页面视觉内容。",
    "clarify": "向用户发起澄清或确认。",
    "cronjob": "管理定时任务，默认受控。",
    "delegate_task": "委派子任务，暂未接入平台链路。",
    "execute_code": "执行 Python 脚本处理多步任务，默认受控。",
    "image_gen": "根据文本提示生成图片。",
    "memory": "读写会话记忆，默认受控。",
    "patch": "对文件做精准补丁修改，默认受控。",
    "process": "管理后台进程，默认受控。",
    "read_file": "读取仓库内文本文件。",
    "search_files": "搜索仓库文件或文件内容。",
    "send_message": "发送平台消息，默认受控。",
    "session_search": "搜索历史会话，暂未接入平台链路。",
    "skill_manage": "管理技能，默认受控。",
    "skill_view": "查看技能内容。",
    "skills_list": "列出可用技能。",
    "text_to_speech": "将文字转换为语音，默认受控。",
    "todo": "维护当前任务清单。",
    "vision_analyze": "分析图片内容。",
    "web_extractor": "从网页 URL 抽取正文内容。",
    "web_research": "先搜索再抽取网页正文，生成研究结果。",
    "web_search": "联网搜索资料。",
    "write_file": "写入仓库文件，默认受控。",
}


def _public_toolset_id(toolset: str) -> str:
    if toolset == "hermes":
        return "builtin-tools"
    if toolset.startswith("hermes-"):
        return f"builtin-{toolset.removeprefix('hermes-').replace('_', '-')}"
    return toolset


def _clean_public_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\bhermes_tools\b", "内置工具包", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHermes[- ]?Agent\b", "内置智能体", text, flags=re.IGNORECASE)
    text = re.sub(r"\bHermes\b", "内置智能体", text, flags=re.IGNORECASE)
    text = text.replace("hermes-agent", "内置智能体")
    text = text.replace(".research/hermes-agent", "内置参考目录")
    return text


def _toolset_label(toolset: str, label_key: str | None = None) -> str:
    candidates = [label_key or toolset, toolset]
    if toolset.startswith("builtin-"):
        suffix = toolset.removeprefix("builtin-")
        candidates.extend([f"hermes-{suffix}", f"hermes-{suffix.replace('-', '_')}"])
    for candidate in candidates:
        if candidate in TOOLSET_LABELS:
            return _clean_public_text(TOOLSET_LABELS[candidate])
    return _clean_public_text(toolset)


def _toolset_payload(toolset: str, label_key: str | None = None) -> dict[str, Any]:
    public_id = _public_toolset_id(toolset)
    return {
        "id": public_id,
        "label": _toolset_label(public_id, label_key),
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
        return "该能力还没有接入 OpsCore 会话、审批和审计链路。"
    return "该工具涉及本地写入、代码执行、进程、计划任务或平台外发，默认不暴露给模型。"


def _registered_tool_item(tool: Any) -> dict[str, Any]:
    item = tool.public_dict()
    raw_toolset = str(item.get("toolset") or tool.toolset)
    description = (
        BUILTIN_TOOL_DESCRIPTIONS.get(str(item.get("name") or ""))
        if raw_toolset.startswith("hermes-")
        else item.get("description")
    )
    item.update(
        {
            "toolset": _public_toolset_id(raw_toolset),
            "label": _clean_public_text(item.get("label") or item.get("name")),
            "description": _clean_public_text(description),
            "status": "available",
            "status_label": _status_label("available"),
            "model_exposed": True,
            "execution_enabled": True,
            "source": "builtin" if raw_toolset.startswith("hermes-") else "opscore",
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
        raw_toolset = f"hermes-{item['toolset']}" if item else "hermes-controlled"
        status = "not_wired" if name in NOT_WIRED_HERMES_TOOLS or item is None else "controlled"
        reason = _controlled_reason(name)
        if item is None and load_problem:
            reason = f"工具元数据加载失败：{_clean_public_text(load_problem)}"

        items.append(
            {
                "name": name,
                "label": _clean_public_text(TOOL_LABELS.get(name, name)),
                "toolset": _public_toolset_id(raw_toolset),
                "scope": "base",
                "description": _clean_public_text(BUILTIN_TOOL_DESCRIPTIONS.get(name) or schema.get("description") or ""),
                "safety_category": "local_write" if name in {"write_file", "patch", "skill_manage"} else "local_execute",
                "protocols": [],
                "asset_types": [],
                "requires_virtual": False,
                **tool_runtime_metadata(
                    name,
                    raw_toolset,
                    "local_write" if name in {"write_file", "patch", "skill_manage"} else "local_execute",
                    "base",
                ),
                "enabled": False,
                "status": status,
                "status_label": _status_label(status),
                "model_exposed": False,
                "execution_enabled": False,
                "source": "builtin",
                "control_reason": reason,
            }
        )
    return items


def build_tool_center_catalog(tool_registry: Any) -> dict[str, Any]:
    registered_tools = tool_registry.all_tools()
    registered_names = {tool.name for tool in registered_tools}
    toolsets: dict[str, dict[str, Any]] = {}

    for tool in registered_tools:
        public_toolset = _public_toolset_id(str(tool.toolset))
        bucket = toolsets.setdefault(public_toolset, _toolset_payload(str(tool.toolset)))
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
