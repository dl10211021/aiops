from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from core.session_profile import generate_session_profile, get_session_profile


class SessionProfileServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def get_session_profile_record(
    session_id: str,
    loader: Callable[[str], dict[str, Any] | None] = get_session_profile,
) -> dict[str, Any] | None:
    return await asyncio.to_thread(loader, session_id)


async def generate_session_profile_record(
    session_id: str,
    model_name: str | None = None,
    include_inspection: bool = True,
    generator: Callable[..., Awaitable[dict[str, Any]]] = generate_session_profile,
) -> dict[str, Any]:
    try:
        return await generator(
            session_id,
            model_name=model_name,
            include_inspection=include_inspection,
        )
    except ValueError as exc:
        raise SessionProfileServiceError(404, str(exc)) from exc
