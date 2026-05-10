from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from core import memory as memory_module
from core.protocol_verification import (
    build_asset_matrix,
    build_overview,
    build_status_overview,
    list_verification_runs,
    run_asset_verification,
)


class ProtocolVerificationServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


_OVERVIEW_CACHE_TTL_SECONDS = 15.0
_overview_cache_lock = threading.Lock()
_overview_cache: tuple[float, dict[str, Any]] | None = None
_status_overview_cache: tuple[float, dict[str, Any]] | None = None


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def invalidate_protocol_verification_overview_cache() -> None:
    global _overview_cache, _status_overview_cache
    with _overview_cache_lock:
        _overview_cache = None
        _status_overview_cache = None


def build_protocol_verification_overview(memory_db: Any | None = None) -> dict[str, Any]:
    global _overview_cache
    if memory_db is None:
        now = time.monotonic()
        with _overview_cache_lock:
            if _overview_cache and _overview_cache[0] > now:
                return _overview_cache[1]

    store = _resolve_memory_db(memory_db)
    overview = build_overview(store.get_all_assets())
    if memory_db is None:
        with _overview_cache_lock:
            _overview_cache = (time.monotonic() + _OVERVIEW_CACHE_TTL_SECONDS, overview)
    return overview


def build_protocol_verification_status_overview(memory_db: Any | None = None) -> dict[str, Any]:
    global _status_overview_cache
    if memory_db is None:
        now = time.monotonic()
        with _overview_cache_lock:
            if _status_overview_cache and _status_overview_cache[0] > now:
                return _status_overview_cache[1]

    store = _resolve_memory_db(memory_db)
    overview = build_status_overview(store.get_all_assets())
    if memory_db is None:
        with _overview_cache_lock:
            _status_overview_cache = (time.monotonic() + _OVERVIEW_CACHE_TTL_SECONDS, overview)
    return overview


def get_protocol_verification_asset(asset_id: int, memory_db: Any | None = None) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    asset = store.get_asset(asset_id)
    if not asset:
        raise ProtocolVerificationServiceError(404, "资产不存在")
    return asset


def build_protocol_verification_matrix(asset_id: int, memory_db: Any | None = None) -> dict[str, Any]:
    return build_asset_matrix(get_protocol_verification_asset(asset_id, memory_db=memory_db))


async def run_protocol_verification_for_asset(
    asset_id: int,
    memory_db: Any | None = None,
) -> dict[str, Any]:
    asset = await asyncio.to_thread(get_protocol_verification_asset, asset_id, memory_db)
    return await run_asset_verification(asset)


def list_protocol_verification_run_records(asset_id: int, limit: int = 20) -> list[dict[str, Any]]:
    return list_verification_runs(asset_id=asset_id, limit=limit)
