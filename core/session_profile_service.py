from __future__ import annotations

import asyncio
import copy
import time
from collections.abc import Awaitable, Callable
from typing import Any

from core.session_profile import generate_session_profile, get_session_profile


class SessionProfileServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


SESSION_PROFILE_CACHE_TTL_SECONDS = 5 * 60
_session_profile_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def clear_session_profile_cache(session_id: str | None = None) -> None:
    if session_id is None:
        _session_profile_cache.clear()
        return
    _session_profile_cache.pop(session_id, None)


def _cached_session_profile(session_id: str) -> dict[str, Any] | None:
    cached = _session_profile_cache.get(session_id)
    if cached is None:
        return None
    cached_at, profile = cached
    if time.monotonic() - cached_at >= SESSION_PROFILE_CACHE_TTL_SECONDS:
        _session_profile_cache.pop(session_id, None)
        return None
    return copy.deepcopy(profile)


def _store_session_profile_cache(session_id: str, profile: dict[str, Any] | None) -> None:
    if not isinstance(profile, dict):
        clear_session_profile_cache(session_id)
        return
    _session_profile_cache[session_id] = (time.monotonic(), copy.deepcopy(profile))


async def get_session_profile_record(
    session_id: str,
    loader: Callable[[str], dict[str, Any] | None] = get_session_profile,
) -> dict[str, Any] | None:
    if loader is get_session_profile:
        cached = _cached_session_profile(session_id)
        if cached is not None:
            return cached
    profile = await asyncio.to_thread(loader, session_id)
    if loader is get_session_profile:
        _store_session_profile_cache(session_id, profile)
        return _cached_session_profile(session_id)
    return profile


async def generate_session_profile_record(
    session_id: str,
    model_name: str | None = None,
    include_inspection: bool = True,
    generator: Callable[..., Awaitable[dict[str, Any]]] = generate_session_profile,
) -> dict[str, Any]:
    try:
        profile = await generator(
            session_id,
            model_name=model_name,
            include_inspection=include_inspection,
        )
        if generator is generate_session_profile:
            _store_session_profile_cache(session_id, profile)
        return profile
    except ValueError as exc:
        raise SessionProfileServiceError(404, str(exc)) from exc
