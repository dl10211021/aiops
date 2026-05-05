from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from core.agent_ltm import retrieve_ltm_context_with_references
from core.agent_message_history import build_chat_message_history
from core.agent_prompts import render_chat_system_prompt
from core.agent_session_context import AgentSessionContext, build_agent_session_context
from core.agent_profiles import load_agent_profile_prompt
from core.assistant_model_config import assistant_task_enabled
from core.knowledge_base_service import build_vault_rag_context_for_prompt
from core.session_profile import profile_to_system_prompt


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
    ltm_result = await retrieve_ltm_context_with_references(
        memory_store=memory_store,
        session_id=session_id,
        user_message=user_message,
        emb_client=emb_client,
        embedding_model=embedding_model,
        memory_scope_ids=session_context.memory_scope_ids(),
        event_logger=event_logger,
    )
    rag_context = ""
    rag_references: list[dict[str, Any]] = []
    try:
        rag_result = build_vault_rag_context_for_prompt(user_message, limit=4)
        rag_context = str(rag_result.get("context") or "")
        rag_references = list(rag_result.get("references") or [])
    except Exception as exc:
        event_logger.error(f"RAG retrieve error: {exc}")

    system_prompt = render_chat_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        skill_instructions=dispatcher.get_skill_instructions(
            active_skills,
            allow_local_scripts=session_context.local_skill_scripts_allowed,
        ),
        ltm_context=ltm_result.context,
        asset_profile_prompt=profile_to_system_prompt(
            memory_store.get_asset_profile(session_id)
            if assistant_task_enabled("asset_profile_prompt") and hasattr(memory_store, "get_asset_profile")
            else None
        ),
        rag_context=rag_context,
    )
    messages = build_chat_message_history(
        memory_store=memory_store,
        session_id=session_id,
        system_prompt=system_prompt,
        user_message=user_message,
        user_display_message=user_display_message,
        user_attachments=user_attachments or [],
        model_name=model_name,
    )
    context = session_context.tool_context()
    tools = dispatcher.get_available_tools(context)

    return ChatAgentRun(
        model_name=model_name,
        embedding_client=emb_client,
        embedding_model=embedding_model,
        session_context=session_context,
        messages=messages,
        context=context,
        tools=tools,
        memory_references=ltm_result.references + rag_references,
    )
