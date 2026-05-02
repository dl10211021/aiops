from __future__ import annotations

import logging
import os


DEFAULT_OPSCORE_HOST = "0.0.0.0"
DEFAULT_OPSCORE_PORT = 8000
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:8000,"
    "http://127.0.0.1:8000,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)
LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def get_runtime_host() -> str:
    return os.environ.get("OPSCORE_HOST", DEFAULT_OPSCORE_HOST).strip() or DEFAULT_OPSCORE_HOST


def get_runtime_port() -> int:
    raw_port = os.environ.get("OPSCORE_PORT", str(DEFAULT_OPSCORE_PORT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("OPSCORE_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("OPSCORE_PORT must be between 1 and 65535")
    return port


def get_log_level() -> int:
    raw_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    return LOG_LEVELS.get(raw_level, logging.INFO)


def get_allowed_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.environ.get("OPSCORE_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",")
        if origin.strip()
    ]
