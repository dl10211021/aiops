import os
import json
import asyncio
import logging
import time
from typing import Dict, Any, List

from core.dispatcher_api_tools import API_TOOL_NAMES, execute_api_tool
from core.dispatcher_database_tools import DATABASE_TOOL_NAMES, execute_database_tool
from core.dispatcher_hermes_tools import HERMES_DISPATCH_TOOL_NAMES, execute_hermes_dispatch_tool
from core.dispatcher_memory_tools import MEMORY_TOOL_NAMES, execute_memory_tool
from core.dispatcher_scope_tools import execute_on_scope_tool
from core.dispatcher_session_tools import SESSION_TOOL_NAMES, execute_session_tool
from core.dispatcher_skill_evolution import (
    atomic_write_text,
    backup_existing_skill_file,
    execute_skill_evolution_tool,
)
from core.dispatcher_utility_tools import UTILITY_TOOL_NAMES, execute_utility_tool
from core.local_script_execution import execute_local_script, validate_local_execution
from core.safety_policy import (
    check_approval_needed as policy_check_approval_needed,
    check_hard_block,
    check_readonly_block,
)
from core.skill_lifecycle import validate_skill_frontmatter
from core.skill_registry_scanner import (
    format_skills_for_ui,
    parse_installed_skill_md,
    parse_market_skill_md,
)
from core.tool_policy_response import blocked_tool_response
from core.tool_registry import tool_registry

logger = logging.getLogger(__name__)


def _blocked_tool_response(tool_call_name: str, args: dict, context: dict, reason: str) -> str:
    return blocked_tool_response(tool_call_name, args, context, reason)


class SkillDispatcher:
    """
    【新版核心】：基于 Markdown 驱动的 Skill 动态扫描器。
    它会自动扫描配置目录下的 SKILL.md，提取名称和说明并将其转化为可供大模型感知的上下文本。
    """

    def __init__(self):
        self.skills_registry = {}
        self.pending_approvals = {}
        self.pending_interactions = {}
        self._last_refresh_time = 0
        self._refresh_interval = 30  # 30 秒缓存，避免每次调用都全量扫描文件系统
        self.skill_directories = [
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "skills"
            ),  # 项目自带技能
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
            ),  # 你的专属私有技能目录
        ]
        # 外部插件市场目录（只看，不用，可点击复制入库）
        self.market_directories = [
            os.path.expanduser(r"~/.gemini/skills"),
            r"D:\AI\.claude\skills",
        ]
        self.refresh_skills()

    def refresh_skills(self, force: bool = False):
        """扫描目录并解析所有 SKILL.md，带时间戳缓存"""
        now = time.time()
        if (
            not force
            and (now - self._last_refresh_time) < self._refresh_interval
            and self.skills_registry
        ):
            return  # 缓存尚未过期，跳过全量扫描

        new_registry = {}

        for base_dir in self.skill_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")

                if os.path.isdir(folder_path) and os.path.exists(skill_md_path):
                    try:
                        skill = parse_installed_skill_md(skill_md_path, folder_path)
                        if skill:
                            new_registry[skill["id"]] = skill
                    except Exception as e:
                        logger.error(f"解析 {skill_md_path} 失败: {e}")

        self.skills_registry = new_registry
        self._last_refresh_time = time.time()

    def _parse_skill_md(self, md_path: str, folder_path: str, registry: dict):
        """解析带有 YAML frontmatter 的 Markdown 文件"""
        skill = parse_installed_skill_md(md_path, folder_path)
        if skill:
            registry[skill["id"]] = skill

    def get_all_registered_skills(self) -> List[Dict[str, Any]]:
        """给前端提供本地已安装技能的摘要信息"""
        self.refresh_skills()
        return format_skills_for_ui(self.skills_registry.values())

    def get_market_skills(self) -> List[Dict[str, Any]]:
        """扫描外部插件市场，但不入库，仅供前端展示和复制"""
        market_skills = []
        for base_dir in self.market_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")

                if os.path.isdir(folder_path) and os.path.exists(skill_md_path):
                    # 如果该文件夹名已经在本地有了，就不在市场里展示为可下载（避免重复）
                    if skill_folder in self.skills_registry:
                        continue

                    try:
                        skill = parse_market_skill_md(skill_md_path, folder_path)
                        if skill:
                            market_skills.append(skill)
                    except Exception as e:
                        logger.error(f"解析市场卡带 {skill_md_path} 失败: {e}")

        return format_skills_for_ui(market_skills)

    def _format_skills_for_ui(self, skills_list) -> List[Dict[str, Any]]:
        """通用UI格式化"""
        return format_skills_for_ui(skills_list)

    def get_skill_instructions(
        self, active_skill_ids: List[str], allow_local_scripts: bool = True
    ) -> str:
        """把用户勾选的所有技能的说明书（Markdown）拼接到一起，作为系统提示词给 AI 看"""
        instructions = ""
        if active_skill_ids and not allow_local_scripts:
            instructions += (
                "\n\n【协议优先约束】：当前是真实资产的原生协议会话，已挂载 Skill 只能作为知识/SOP 参考；"
                "禁止执行 Skill 中的 python/bash/本地脚本示例，必须使用当前会话暴露的原生协议工具完成操作。\n"
            )
        for s_id in active_skill_ids:
            if s_id in self.skills_registry:
                skill = self.skills_registry[s_id]
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
                instructions += (
                    f"<INSTRUCTIONS>\n{skill['instructions']}\n</INSTRUCTIONS>\n"
                )
                instructions += "</ACTIVATED_SKILL>\n"
        return instructions

    def get_active_skill_paths(self, active_skill_ids: List[str]) -> List[str]:
        self.refresh_skills()
        paths = []
        for s_id in active_skill_ids:
            skill = self.skills_registry.get(s_id)
            if skill and skill.get("source_path"):
                paths.append(os.path.realpath(skill["source_path"]))
        return paths

    def _custom_skills_base(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
        )

    @staticmethod
    def _validate_skill_frontmatter(skill_id: str, content: str) -> tuple[bool, str]:
        return validate_skill_frontmatter(skill_id, content)

    @staticmethod
    def _atomic_write_text(file_path: str, content: str) -> None:
        atomic_write_text(file_path, content)

    @staticmethod
    def _backup_existing_skill_file(file_path: str) -> str | None:
        return backup_existing_skill_file(file_path)

    def _validate_local_execution(
        self, command: str, cwd: str, context: Dict[str, Any]
    ) -> tuple[bool, str]:
        active_paths = context.get("active_skill_paths") or self.get_active_skill_paths(
            context.get("active_skills", [])
        )
        return validate_local_execution(command, cwd, active_paths)

    def check_approval_needed(self, tool_call_name: str, args: dict, context: dict) -> tuple[bool, str]:
        """【安全层】检查当前大模型执行的指令是否需要人类审批。"""
        from connections.ssh_manager import ssh_manager
        
        session_id = context.get("session_id")
        if session_id and session_id in ssh_manager.active_sessions:
            if ssh_manager.active_sessions[session_id]["info"].get("auto_approve_all", False):
                return False, ""
        hard_blocked, _ = check_hard_block(tool_call_name, args, context)
        if hard_blocked:
            return False, ""
        readonly_blocked, _ = check_readonly_block(tool_call_name, args, context)
        if readonly_blocked:
            return False, ""
        return policy_check_approval_needed(tool_call_name, args, context)

    def get_available_tools(

        self, current_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Return protocol-aware tool schemas from the central registry."""
        return tool_registry.get_openai_tools(current_context)

    async def route_and_execute(
        self, tool_call_name: str, args: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """执行大模型的意图"""
        hard_blocked, hard_reason = check_hard_block(tool_call_name, args, context)
        if hard_blocked:
            logger.warning(
                "Hard blocked tool call %s for session %s: %s",
                tool_call_name,
                context.get("session_id"),
                hard_reason,
            )
            return _blocked_tool_response(tool_call_name, args, context, hard_reason)

        if tool_call_name in SESSION_TOOL_NAMES:
            return await execute_session_tool(tool_call_name, args, context, logger)

        elif tool_call_name == "local_execute_script":
            # 这是为了兼容之前的 Gemini Skills，让它能在当前电脑上跑写的 python 脚本
            cmd = args.get("command")
            cwd = args.get("cwd") or os.getcwd()

            is_valid, reason = self._validate_local_execution(cmd, cwd, context)
            if not is_valid:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return _blocked_tool_response(tool_call_name, args, context, reason)

            try:
                return await asyncio.to_thread(execute_local_script, cmd, cwd, logger)
            except Exception as e:
                return json.dumps({"error": str(e)})

        elif tool_call_name in UTILITY_TOOL_NAMES:
            return await execute_utility_tool(tool_call_name, args, logger)

        elif tool_call_name in HERMES_DISPATCH_TOOL_NAMES:
            return await execute_hermes_dispatch_tool(tool_call_name, args, context, logger)

        elif tool_call_name in MEMORY_TOOL_NAMES:
            return await execute_memory_tool(tool_call_name, args, context, logger)

        elif tool_call_name in DATABASE_TOOL_NAMES:
            return await execute_database_tool(tool_call_name, args, context)

        elif tool_call_name in API_TOOL_NAMES:
            return await execute_api_tool(tool_call_name, args, context, self.route_and_execute)

        elif tool_call_name == "execute_on_scope":
            return await execute_on_scope_tool(args, context)

        elif tool_call_name == "evolve_skill":
            return execute_skill_evolution_tool(args, self._custom_skills_base(), self.refresh_skills, logger)

        return '{"error": "Unknown tool"}'


# 全局单例
dispatcher = SkillDispatcher()
