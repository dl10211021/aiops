from __future__ import annotations

import uuid
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from core.request_context import request_id_context
from core.security import is_authorized_request


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-Permitted-Cross-Domain-Policies": "none",
}
SLOW_REQUEST_THRESHOLD_MS = 500
logger = logging.getLogger(__name__)

CallNext = Callable[[Request], Awaitable[Response]]


def resolve_request_id(headers) -> str:
    return headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"


async def dispatch_request_id(request: Request, call_next: CallNext) -> Response:
    request_id = resolve_request_id(request.headers)
    with request_id_context(request_id):
        request.state.request_id = request_id
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def requires_api_token_auth(path: str, method: str) -> bool:
    return path.startswith("/api/v1/") and method != "OPTIONS"


def unauthorized_api_token_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Missing or invalid OpsCore API token"},
    )


async def dispatch_api_token_auth(
    request: Request,
    call_next: CallNext,
    token: str | None,
) -> Response:
    if requires_api_token_auth(request.url.path, request.method):
        if not is_authorized_request(request.headers, token):
            return unauthorized_api_token_response()
    return await call_next(request)


async def dispatch_security_headers(request: Request, call_next: CallNext) -> Response:
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value
    path = getattr(getattr(request, "url", None), "path", "")
    if path.startswith("/assets/") and response.status_code < 400:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-store"
    elif path == "/":
        response.headers["Cache-Control"] = "no-cache"
    return response


async def dispatch_timing_headers(request: Request, call_next: CallNext) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    if request.url.path.startswith("/api/v1/") and elapsed_ms >= SLOW_REQUEST_THRESHOLD_MS:
        logger.warning(
            "Slow request %.1fms %s %s",
            elapsed_ms,
            request.method,
            request.url.path,
        )
    return response
