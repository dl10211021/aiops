from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LtmContextResult:
    context: str
    references: list[dict[str, Any]]


class AgentLongTermMemoryStore(Protocol):
    async def retrieve_ltm(
        self,
        session_id: str,
        user_message: str,
        emb_client: Any,
        embedding_model: str,
        memory_scope_ids: list[str] | None = None,
    ) -> str:
        ...

    async def compress_and_store_ltm(
        self,
        session_id: str,
        emb_client: Any,
        embedding_model: str,
        primary_model_id: str | None = None,
        memory_scope_ids: list[str] | None = None,
    ) -> None:
        ...


async def retrieve_ltm_context(
    *,
    memory_store: AgentLongTermMemoryStore,
    session_id: str,
    user_message: str,
    emb_client: Any,
    embedding_model: str,
    memory_scope_ids: list[str] | None = None,
    event_logger: logging.Logger,
) -> str:
    try:
        return await memory_store.retrieve_ltm(
            session_id,
            user_message,
            emb_client,
            embedding_model,
            memory_scope_ids=memory_scope_ids,
        )
    except Exception as e:
        event_logger.error(f"LTM retrieve error: {e}")
        return ""


async def retrieve_ltm_context_with_references(
    *,
    memory_store: AgentLongTermMemoryStore,
    session_id: str,
    user_message: str,
    emb_client: Any,
    embedding_model: str,
    memory_scope_ids: list[str] | None = None,
    event_logger: logging.Logger,
) -> LtmContextResult:
    try:
        retriever = getattr(memory_store, "retrieve_ltm_with_references", None)
        if callable(retriever):
            context, references = await retriever(
                session_id,
                user_message,
                emb_client,
                embedding_model,
                memory_scope_ids=memory_scope_ids,
            )
            return LtmContextResult(context=context or "", references=references or [])
        context = await memory_store.retrieve_ltm(
            session_id,
            user_message,
            emb_client,
            embedding_model,
            memory_scope_ids=memory_scope_ids,
        )
        return LtmContextResult(context=context or "", references=[])
    except Exception as e:
        event_logger.error(f"LTM retrieve error: {e}")
        return LtmContextResult(context="", references=[])


def schedule_ltm_compression(
    *,
    memory_store: AgentLongTermMemoryStore,
    session_id: str,
    emb_client: Any,
    embedding_model: str,
    primary_model_id: str | None = None,
    memory_scope_ids: list[str] | None = None,
) -> asyncio.Task:
    return asyncio.create_task(
        memory_store.compress_and_store_ltm(
            session_id,
            emb_client,
            embedding_model,
            primary_model_id=primary_model_id,
            memory_scope_ids=memory_scope_ids,
        )
    )
