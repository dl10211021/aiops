from __future__ import annotations

from typing import Any, NoReturn, Protocol

from fastapi import HTTPException


class ServiceHttpError(Protocol):
    status_code: int
    detail: Any


def raise_http_error(exc: ServiceHttpError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
