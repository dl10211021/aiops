"""Service for scanning installed and market Skill bundles."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from core.skill_registry_scanner import (
    format_skills_for_ui,
    parse_installed_skill_md,
    parse_market_skill_md,
)


def default_skill_directories() -> list[str]:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return [
        os.path.join(repo_root, "skills"),
        os.path.join(repo_root, "my_custom_skills"),
    ]


def default_market_directories() -> list[str]:
    return [
        os.path.expanduser(r"~/.gemini/skills"),
        r"D:\AI\.claude\skills",
    ]


class SkillRegistryService:
    """Scan local Skill bundles and expose registry-derived views."""

    def __init__(
        self,
        *,
        skill_directories: list[str] | None = None,
        market_directories: list[str] | None = None,
        refresh_interval: int = 30,
        logger: logging.Logger | None = None,
    ) -> None:
        self.skills_registry: dict[str, dict[str, Any]] = {}
        self.skill_directories = skill_directories or default_skill_directories()
        self.market_directories = market_directories or default_market_directories()
        self._last_refresh_time = 0.0
        self._refresh_interval = refresh_interval
        self._logger = logger or logging.getLogger(__name__)

    def refresh_skills(self, force: bool = False) -> None:
        """Scan configured local directories, with a short cache window."""
        now = time.time()
        if (
            not force
            and (now - self._last_refresh_time) < self._refresh_interval
            and self.skills_registry
        ):
            return

        new_registry: dict[str, dict[str, Any]] = {}
        for base_dir in self.skill_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")
                if not (os.path.isdir(folder_path) and os.path.exists(skill_md_path)):
                    continue

                try:
                    skill = parse_installed_skill_md(skill_md_path, folder_path)
                    if skill:
                        new_registry[skill["id"]] = skill
                except Exception as exc:
                    self._logger.error("解析 %s 失败: %s", skill_md_path, exc)

        self.skills_registry = new_registry
        self._last_refresh_time = time.time()

    def parse_skill_md(
        self,
        md_path: str,
        folder_path: str,
        registry: dict[str, dict[str, Any]],
    ) -> None:
        skill = parse_installed_skill_md(md_path, folder_path)
        if skill:
            registry[skill["id"]] = skill

    def get_all_registered_skills(self) -> list[dict[str, Any]]:
        self.refresh_skills()
        return format_skills_for_ui(self.skills_registry.values())

    def get_market_skills(self) -> list[dict[str, Any]]:
        """Scan external Skill stores for copyable bundles."""
        market_skills: list[dict[str, Any]] = []
        for base_dir in self.market_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")
                if not (os.path.isdir(folder_path) and os.path.exists(skill_md_path)):
                    continue
                if skill_folder in self.skills_registry:
                    continue

                try:
                    skill = parse_market_skill_md(skill_md_path, folder_path)
                    if skill:
                        market_skills.append(skill)
                except Exception as exc:
                    self._logger.error("解析市场卡带 %s 失败: %s", skill_md_path, exc)

        return format_skills_for_ui(market_skills)

    def format_skills_for_ui(self, skills_list) -> list[dict[str, Any]]:
        return format_skills_for_ui(skills_list)

    def get_skill_instructions(
        self,
        active_skill_ids: list[str],
        *,
        allow_local_scripts: bool = True,
    ) -> str:
        instructions = ""
        if active_skill_ids and not allow_local_scripts:
            instructions += (
                "\n\n【协议优先约束】：当前是真实资产的原生协议会话，已挂载 Skill 只能作为知识/SOP 参考；"
                "禁止执行 Skill 中的 python/bash/本地脚本示例，必须使用当前会话暴露的原生协议工具完成操作。\n"
            )
        for skill_id in active_skill_ids:
            if skill_id not in self.skills_registry:
                continue

            skill = self.skills_registry[skill_id]
            source_path = skill.get("source_path", "")
            instructions += f"\n\n<!-- 激活技能: {skill['name']} -->\n"
            instructions += "<ACTIVATED_SKILL>\n"
            if allow_local_scripts:
                instructions += (
                    f"<SKILL_ABSOLUTE_PATH>{source_path}</SKILL_ABSOLUTE_PATH>\n"
                )
                instructions += f"【重要指令】：此技能存放于物理路径 `{source_path}`。当你需要调用此技能内的 python 脚本时，请务必使用绝对路径，或者在使用 `local_execute_script` 工具时将 `cwd` 参数严格设置为该绝对路径，切勿自行猜测。\n"
            else:
                instructions += "【重要指令】：当前会话禁止执行此 Skill 内的本地脚本；其中脚本示例仅作知识参考。\n"
            instructions += f"<INSTRUCTIONS>\n{skill['instructions']}\n</INSTRUCTIONS>\n"
            instructions += "</ACTIVATED_SKILL>\n"
        return instructions

    def get_active_skill_paths(self, active_skill_ids: list[str]) -> list[str]:
        self.refresh_skills()
        paths: list[str] = []
        for skill_id in active_skill_ids:
            skill = self.skills_registry.get(skill_id)
            if skill and skill.get("source_path"):
                paths.append(os.path.realpath(skill["source_path"]))
        return paths
