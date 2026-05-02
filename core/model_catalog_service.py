from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

ModelCatalogFetcher = Callable[..., Awaitable[list[dict[str, Any]]]]


async def fetch_model_catalog(
    *,
    provider_id: str | None = None,
    refresh: bool = False,
    fetcher: ModelCatalogFetcher | None = None,
) -> list[dict[str, Any]]:
    if fetcher is None:
        from core.agent import get_available_models_for_provider as fetcher

    return await fetcher(provider_id=provider_id, refresh=refresh)
