"""Request-scoped context for logging and audit correlation."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator


_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "opscore_request_id",
    default=None,
)


def current_request_id() -> str | None:
    return _request_id_var.get()


@contextmanager
def request_id_context(request_id: str) -> Iterator[None]:
    token = _request_id_var.set(request_id)
    try:
        yield
    finally:
        _request_id_var.reset(token)
