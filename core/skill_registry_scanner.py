"""Skill registry scanning and UI formatting helpers."""

from __future__ import annotations

import os
import re
from typing import Any

import yaml


def _tool_count_from_body(body: str) -> int:
    return max(len(re.findall(r"```", body)) // 2, 1)


def _parse_skill_file(
    md_path: str,
    folder_path: str,
    source_type: str,
    is_market: bool = False,
) -> dict[str, Any] | None:
    with open(md_path, "r", encoding="utf-8") as file:
        content = file.read()

    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()
    skill_id = frontmatter.get("name", os.path.basename(folder_path))

    skill = {
        "id": skill_id,
        "name": skill_id.replace("-", " ").title(),
        "description": frontmatter.get("description", "未提供描述"),
        "instructions": body,
        "source_path": folder_path,
        "source_type": source_type,
        "tool_count": _tool_count_from_body(body),
    }
    if is_market:
        skill["is_market"] = True
    return skill


def installed_skill_source_type(folder_path: str) -> str:
    if r".gemini" in folder_path:
        return "Gemini Global 官方技能库"
    if r".claude" in folder_path:
        return "Claude 自定义技能库"
    if "my_custom_skills" in folder_path:
        return "OpsCore 私有技能"
    return "OpsCore 内置技能"


def market_skill_source_type(folder_path: str) -> str:
    if r".gemini" in folder_path:
        return "Gemini Global 官方技能库"
    if r".claude" in folder_path:
        return "Claude 自定义技能库"
    return "外部未知技能"


def parse_installed_skill_md(md_path: str, folder_path: str) -> dict[str, Any] | None:
    return _parse_skill_file(
        md_path,
        folder_path,
        installed_skill_source_type(folder_path),
    )


def parse_market_skill_md(md_path: str, folder_path: str) -> dict[str, Any] | None:
    return _parse_skill_file(
        md_path,
        folder_path,
        market_skill_source_type(folder_path),
        is_market=True,
    )


def format_skills_for_ui(skills_list) -> list[dict[str, Any]]:
    result = []
    for skill in skills_list:
        extracted_tools = []
        for line in skill["instructions"].split("\n"):
            line = line.strip()
            if line.startswith("- **") or line.startswith("### "):
                clean_line = (
                    line.replace("- **", "")
                    .replace("**:", "")
                    .replace("###", "")
                    .strip()
                )
                if 2 < len(clean_line) < 30:
                    extracted_tools.append(clean_line)

        if not extracted_tools:
            extracted_tools = ["基于 Markdown 的自定义指令"]

        result.append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "description": skill["description"],
                "tool_count": skill["tool_count"],
                "tools": list(set(extracted_tools))[:6],
                "source_path": skill["source_path"],
                "source_type": skill["source_type"],
                "is_market": skill.get("is_market", False),
            }
        )

    return result
