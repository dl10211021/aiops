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


def _asset_key_for_session_context(session_context: AgentSessionContext) -> str:
    asset_type = session_context.asset_type or "asset"
    protocol = session_context.protocol or "unknown"
    return f"{asset_type}:{protocol}:{session_context.host}:{session_context.port or ''}"


def _load_asset_profile_for_prompt(
    memory_store: ChatAgentMemoryStore,
    session_id: str,
    session_context: AgentSessionContext,
) -> dict | None:
    if not assistant_task_enabled("asset_profile_prompt"):
        return None
    exact_loader = getattr(memory_store, "get_asset_profile", None)
    if callable(exact_loader):
        profile = exact_loader(session_id)
        if profile:
            return profile
    return None


def _preview_text(text: Any, limit: int = 260) -> str:
    preview = " ".join(str(text or "").split())
    if len(preview) <= limit:
        return preview
    return preview[: limit - 1].rstrip() + "..."


def _base_prompt_reference(
    *,
    session_id: str,
    agent_profile: str,
    base_prompt: str,
) -> dict[str, Any] | None:
    if not str(base_prompt or "").strip():
        return None
    return {
        "source_type": "system_prompt",
        "kind": "agent_profile",
        "kind_label": "默认提示词",
        "title": f"会话角色：{agent_profile or 'default'}",
        "scope_id": session_id,
        "source_session_id": session_id,
        "summary_preview": _preview_text(base_prompt),
    }


def _asset_profile_reference(
    *,
    session_id: str,
    session_context: AgentSessionContext,
    profile: dict | None,
) -> dict[str, Any] | None:
    if not profile:
        return None
    title = (
        profile.get("role_label")
        or profile.get("remark")
        or profile.get("host")
        or session_context.host
        or "资产画像"
    )
    summary = (
        profile.get("profile_prompt")
        or profile.get("source_summary")
        or profile.get("purpose")
        or ""
    )
    return {
        "source_type": "asset_profile",
        "kind": "asset_profile_prompt",
        "kind_label": "资产画像",
        "title": str(title),
        "scope_id": session_id,
        "source_session_id": profile.get("session_id") or session_id,
        "updated_at": profile.get("updated_at"),
        "summary_preview": _preview_text(summary),
        "path": f"asset_profiles/{profile.get('session_id') or session_id}",
    }


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
    base_prompt_ref = _base_prompt_reference(
        session_id=session_id,
        agent_profile=agent_profile,
        base_prompt=base_prompt,
    )
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

    asset_profile = _load_asset_profile_for_prompt(memory_store, session_id, session_context)
    asset_profile_ref = _asset_profile_reference(
        session_id=session_id,
        session_context=session_context,
        profile=asset_profile,
    )
    system_prompt = render_chat_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        skill_instructions=dispatcher.get_skill_instructions(
            active_skills,
            allow_local_scripts=session_context.local_skill_scripts_allowed,
        ),
        ltm_context=ltm_result.context,
        asset_profile_prompt=profile_to_system_prompt(asset_profile),
        rag_context=rag_context,
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
    context = session_context.tool_context()
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
        memory_references=[
            ref
            for ref in [base_prompt_ref, asset_profile_ref, *ltm_result.references, *rag_references]
            if ref
        ],
    )
