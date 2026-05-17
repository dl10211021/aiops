from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.agent_ltm import retrieve_ltm_context_with_references
from core.agent_session_context import AgentSessionContext
from core.assistant_model_config import assistant_task_enabled
from core.knowledge_base_service import build_vault_rag_context_for_prompt
from core.session_profile import profile_to_system_prompt


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


def _load_asset_profile_for_prompt(
    memory_store: Any,
    session_id: str,
) -> dict | None:
    if not assistant_task_enabled("asset_profile_prompt"):
        return None
    exact_loader = getattr(memory_store, "get_asset_profile", None)
    if callable(exact_loader):
        profile = exact_loader(session_id)
        if profile:
            return profile
    return None


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
class ChatContextBundle:
    ltm_context: str
    rag_context: str
    asset_profile_prompt: str
    references: list[dict[str, Any]]

    @property
    def has_ltm_context(self) -> bool:
        return bool(str(self.ltm_context or "").strip())

    @property
    def has_rag_context(self) -> bool:
        return bool(str(self.rag_context or "").strip())

    @property
    def has_asset_profile(self) -> bool:
        return bool(str(self.asset_profile_prompt or "").strip())


async def build_chat_context_bundle(
    *,
    memory_store: Any,
    session_id: str,
    session_context: AgentSessionContext,
    agent_profile: str,
    base_prompt: str,
    user_message: str,
    emb_client: Any,
    embedding_model: str,
    event_logger: logging.Logger,
) -> ChatContextBundle:
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

    asset_profile = _load_asset_profile_for_prompt(memory_store, session_id)
    asset_profile_ref = _asset_profile_reference(
        session_id=session_id,
        session_context=session_context,
        profile=asset_profile,
    )

    return ChatContextBundle(
        ltm_context=ltm_result.context,
        rag_context=rag_context,
        asset_profile_prompt=profile_to_system_prompt(asset_profile),
        references=[
            ref
            for ref in [
                base_prompt_ref,
                asset_profile_ref,
                *ltm_result.references,
                *rag_references,
            ]
            if ref
        ],
    )
