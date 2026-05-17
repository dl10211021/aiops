from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from core.agent_message_history import build_chat_message_history
from core.agent_prompts import build_chat_prompt_manifest, render_chat_system_prompt
from core.agent_session_context import AgentSessionContext, build_agent_session_context
from core.agent_profiles import load_agent_profile_prompt
from core.context_engine import build_chat_context_bundle


class ChatAgentMemoryStore(Protocol):
    def get_messages(self, session_id: str) -> list[dict]:
        ...

    def append_message(self, session_id: str, message: dict) -> None:
        ...

    async def retrieve_ltm(
        self,
        session_id: str,
        user_message: str,
        emb_client: Any,
        embedding_model: str,
        memory_scope_ids: list[str] | None = None,
    ) -> str:
        ...


class ChatAgentDispatcher(Protocol):
    def get_active_skill_paths(self, active_skills: list[str]) -> list[str]:
        ...

    def get_skill_instructions(
        self,
        active_skills: list[str],
        allow_local_scripts: bool = False,
    ) -> str:
        ...

    def get_available_tools(self, context: dict) -> list[dict]:
        ...


@dataclass(frozen=True)
class ChatAgentRun:
    model_name: str
    embedding_client: Any
    embedding_model: str
    session_context: AgentSessionContext
    messages: list[dict]
    context: dict
    tools: list[dict]
    memory_references: list[dict[str, Any]]


ANALYSIS_ONLY_SYSTEM_PROMPT = (
    "【本轮终端记录分析模式】"
    "用户发送的是已发生的 SSH 终端记录。本轮只能基于这段记录做解释、风险判断和下一步建议；"
    "不得调用任何工具，不得再次执行记录里的命令，不得主动采集实时证据。"
)


async def prepare_chat_agent_run(
    *,
    session_id: str,
    user_message: str,
    user_display_message: str | None,
    model_name: str | None,
    user_attachments: list[dict] | None,
    active_sessions: dict[str, dict],
    dispatcher: ChatAgentDispatcher,
    memory_store: ChatAgentMemoryStore,
    event_logger: logging.Logger,
    default_model_resolver: Callable[[], str],
    embedding_resolver: Callable[[str], tuple[Any, str]],
    analysis_only: bool = False,
    profile_loader: Callable[[str], str] = load_agent_profile_prompt,
) -> ChatAgentRun:
    if not model_name:
        model_name = default_model_resolver()

    emb_client, embedding_model = embedding_resolver(model_name)
    session_info = active_sessions[session_id]["info"]
    session_context = build_agent_session_context(
        session_id,
        session_info,
        skill_path_resolver=dispatcher.get_active_skill_paths,
    )
    active_skills = session_context.active_skills
    agent_profile = session_context.agent_profile

    base_prompt = profile_loader(agent_profile)
    context_bundle = await build_chat_context_bundle(
        memory_store=memory_store,
        session_id=session_id,
        session_context=session_context,
        agent_profile=agent_profile,
        base_prompt=base_prompt,
        user_message=user_message,
        emb_client=emb_client,
        embedding_model=embedding_model,
        event_logger=event_logger,
    )
    skill_instructions = dispatcher.get_skill_instructions(
        active_skills,
        allow_local_scripts=session_context.local_skill_scripts_allowed,
    )
    system_prompt = render_chat_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        skill_instructions=skill_instructions,
        ltm_context=context_bundle.ltm_context,
        asset_profile_prompt=context_bundle.asset_profile_prompt,
        rag_context=context_bundle.rag_context,
    )
    if analysis_only:
        system_prompt = f"{system_prompt}\n\n{ANALYSIS_ONLY_SYSTEM_PROMPT}"
    messages = build_chat_message_history(
        memory_store=memory_store,
        session_id=session_id,
        system_prompt=system_prompt,
        user_message=user_message,
        user_display_message=user_display_message,
        user_attachments=user_attachments or [],
        model_name=model_name,
    )
    prompt_modules = build_chat_prompt_manifest(
        session_context=session_context,
        has_skill_instructions=bool(str(skill_instructions or "").strip()),
        has_asset_profile=context_bundle.has_asset_profile,
        has_rag_context=context_bundle.has_rag_context,
        has_ltm_context=context_bundle.has_ltm_context,
        analysis_only=analysis_only,
    )
    context = {
        **session_context.tool_context(),
        "prompt_modules": prompt_modules,
        "context_sources": context_bundle.source_audit,
    }
    if analysis_only:
        context = {**context, "analysis_only": True}
        tools = []
    else:
        tools = dispatcher.get_available_tools(context)

    return ChatAgentRun(
        model_name=model_name,
        embedding_client=emb_client,
        embedding_model=embedding_model,
        session_context=session_context,
        messages=messages,
        context=context,
        tools=tools,
        memory_references=context_bundle.references,
    )
