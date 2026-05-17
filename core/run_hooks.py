from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from core.redaction import redact_value


RunHookHandler = Callable[[str, dict[str, Any]], Any]

logger = logging.getLogger(__name__)

_handlers: dict[str, list[RunHookHandler]] = {}


def register_run_hook(event_type: str, handler: RunHookHandler) -> Callable[[], None]:
    """Register an in-process run hook handler and return an unregister callback."""
    normalized = str(event_type or "").strip()
    if not normalized:
        raise ValueError("event_type is required")
    _handlers.setdefault(normalized, []).append(handler)

    def unregister() -> None:
        handlers = _handlers.get(normalized)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            return
        if not handlers:
            _handlers.pop(normalized, None)

    return unregister


def clear_run_hooks() -> None:
    """Clear all registered hook handlers. Intended for tests and local resets."""
    _handlers.clear()


async def emit_run_hook(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Emit a lifecycle event.

    Hook failures are logged and swallowed so observability/learning consumers
    cannot break the main execution path. Policy gates should remain explicit
    services, not passive hooks.
    """
    normalized = str(event_type or "").strip()
    if not normalized:
        return
    event_payload = _build_event_payload(normalized, payload or {})
    for handler in _matching_handlers(normalized):
        try:
            result = handler(normalized, event_payload)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("run hook failed: %s", normalized)


def _build_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_value(payload)
    return {
        "event_type": event_type,
        "emitted_at": time.time(),
        "payload": redacted if isinstance(redacted, dict) else {},
    }


def _matching_handlers(event_type: str) -> list[RunHookHandler]:
    handlers = list(_handlers.get(event_type, []))
    if ":" in event_type:
        family = event_type.split(":", 1)[0]
        handlers.extend(_handlers.get(f"{family}:*", []))
    handlers.extend(_handlers.get("*", []))
    return handlers
