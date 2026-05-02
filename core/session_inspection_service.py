from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from core.session_inspector import inspect_session


async def inspect_active_session_record(
    session_id: str,
    inspector: Callable[[str], Awaitable[dict[str, Any]]] = inspect_session,
) -> dict[str, Any]:
    return await inspector(session_id)
