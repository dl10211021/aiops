from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol


class AgentLongTermMemoryStore(Protocol):
    async def retrieve_ltm(
        self,
        session_id: str,
        user_message: str,
        emb_client: Any,
        embedding_model: str,
    ) -> str:
        ...

    async def compress_and_store_ltm(
        self,
        session_id: str,
        emb_client: Any,
        embedding_model: str,
        primary_model_id: str | None = None,
    ) -> None:
        ...


async def retrieve_ltm_context(
    *,
    memory_store: AgentLongTermMemoryStore,
    session_id: str,
    user_message: str,
    emb_client: Any,
    embedding_model: str,
    event_logger: logging.Logger,
) -> str:
    try:
        return await memory_store.retrieve_ltm(
            session_id,
            user_message,
            emb_client,
            embedding_model,
        )
    except Exception as e:
        event_logger.error(f"LTM retrieve error: {e}")
        return ""


def schedule_ltm_compression(
    *,
    memory_store: AgentLongTermMemoryStore,
    session_id: str,
    emb_client: Any,
    embedding_model: str,
    primary_model_id: str | None = None,
) -> asyncio.Task:
    return asyncio.create_task(
        memory_store.compress_and_store_ltm(
            session_id,
            emb_client,
            embedding_model,
            primary_model_id,
        )
    )
