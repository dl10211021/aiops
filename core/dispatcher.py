import os
import json
import asyncio
import logging
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
from core.skill_registry_service import SkillRegistryService
from core.tool_execution_policy import ToolExecutionGate, evaluate_tool_execution_gate
from core.tool_policy_response import blocked_tool_response
from core.tool_registry import tool_policy_metadata, tool_registry

logger = logging.getLogger(__name__)


def _blocked_tool_response(tool_call_name: str, args: dict, context: dict, reason: str) -> str:
    return blocked_tool_response(tool_call_name, args, context, reason)


class SkillDispatcher:
    """
    【新版核心】：基于 Markdown 驱动的 Skill 动态扫描器。
    它会自动扫描配置目录下的 SKILL.md，提取名称和说明并将其转化为可供大模型感知的上下文本。
    """

    def __init__(self):
        self.pending_approvals = {}
        self.pending_interactions = {}
        self.skill_registry_service = SkillRegistryService(logger=logger)
        self.skills_registry = self.skill_registry_service.skills_registry
        self.skill_directories = self.skill_registry_service.skill_directories
        self.market_directories = self.skill_registry_service.market_directories
        self._last_refresh_time = self.skill_registry_service._last_refresh_time
        self._refresh_interval = self.skill_registry_service._refresh_interval
        self.refresh_skills()

    def _get_skill_registry_service(self) -> SkillRegistryService:
        service = getattr(self, "skill_registry_service", None)
        if service is None:
            service = SkillRegistryService(
                skill_directories=getattr(self, "skill_directories", None),
                market_directories=getattr(self, "market_directories", None),
                refresh_interval=getattr(self, "_refresh_interval", 30),
                logger=logger,
            )
            existing_registry = getattr(self, "skills_registry", None)
            if existing_registry:
                service.skills_registry = existing_registry
            self.skill_registry_service = service
            self.skill_directories = service.skill_directories
            self.market_directories = service.market_directories
            self._refresh_interval = service._refresh_interval
        return service

    def _sync_skill_registry_state(self) -> None:
        service = self._get_skill_registry_service()
        self.skills_registry = service.skills_registry
        self.skill_directories = service.skill_directories
        self.market_directories = service.market_directories
        self._last_refresh_time = service._last_refresh_time
        self._refresh_interval = service._refresh_interval

    def refresh_skills(self, force: bool = False):
        """扫描目录并解析所有 SKILL.md，带时间戳缓存"""
        service = self._get_skill_registry_service()
        service.refresh_skills(force=force)
        self._sync_skill_registry_state()

    def _parse_skill_md(self, md_path: str, folder_path: str, registry: dict):
        """解析带有 YAML frontmatter 的 Markdown 文件"""
        self._get_skill_registry_service().parse_skill_md(md_path, folder_path, registry)

    def get_all_registered_skills(self) -> List[Dict[str, Any]]:
        """给前端提供本地已安装技能的摘要信息"""
        self.refresh_skills()
        return self._get_skill_registry_service().format_skills_for_ui(
            self.skills_registry.values()
        )

    def get_market_skills(self) -> List[Dict[str, Any]]:
        """扫描外部插件市场，但不入库，仅供前端展示和复制"""
        service = self._get_skill_registry_service()
        service.skills_registry = self.skills_registry
        return service.get_market_skills()

    def _format_skills_for_ui(self, skills_list) -> List[Dict[str, Any]]:
        """通用UI格式化"""
        return self._get_skill_registry_service().format_skills_for_ui(skills_list)

    def get_skill_instructions(
        self, active_skill_ids: List[str], allow_local_scripts: bool = True
    ) -> str:
        """把用户勾选的所有技能的说明书（Markdown）拼接到一起，作为系统提示词给 AI 看"""
        service = self._get_skill_registry_service()
        service.skills_registry = self.skills_registry
        return service.get_skill_instructions(
            active_skill_ids,
            allow_local_scripts=allow_local_scripts,
        )

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
        gate = self.check_execution_gate(tool_call_name, args, context)
        return gate.approval_required, gate.reason

    def check_execution_gate(
        self,
        tool_call_name: str,
        args: dict,
        context: dict,
        *,
        policy: dict[str, Any] | None = None,
    ) -> ToolExecutionGate:
        """返回统一的执行闸门，包含审批来源、原因和策略。"""
        from connections.ssh_manager import ssh_manager

        session_id = context.get("session_id")
        hard_blocked, _ = check_hard_block(tool_call_name, args, context)
        if hard_blocked:
            return ToolExecutionGate(approval_required=False, reason="", policy=tool_policy_metadata(tool_call_name), approval_sources=())
        readonly_blocked, _ = check_readonly_block(tool_call_name, args, context)
        if readonly_blocked:
            return ToolExecutionGate(approval_required=False, reason="", policy=tool_policy_metadata(tool_call_name), approval_sources=())

        runtime_gate = evaluate_tool_execution_gate(
            tool_call_name,
            policy=policy or tool_policy_metadata(tool_call_name),
        )
        if runtime_gate.approval_required:
            return runtime_gate

        if session_id and session_id in ssh_manager.active_sessions:
            if ssh_manager.active_sessions[session_id]["info"].get("auto_approve_all", False):
                return ToolExecutionGate(
                    False,
                    "",
                    runtime_gate.policy,
                    tuple(runtime_gate.approval_sources),
                )

        needs_approval, reason = policy_check_approval_needed(tool_call_name, args, context)
        gate = evaluate_tool_execution_gate(
            tool_call_name,
            safety_needs_approval=needs_approval,
            safety_reason=reason,
            policy=runtime_gate.policy,
        )
        return gate

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
