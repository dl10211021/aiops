from __future__ import annotations

import time
from typing import Any

from connections import db_manager


CACHE_TTL_SECONDS = 60
_oracle_client_cache: tuple[float, dict[str, Any]] | None = None
_driver_capabilities_cache: tuple[float, dict[str, Any]] | None = None


def clear_database_capabilities_cache() -> None:
    global _oracle_client_cache, _driver_capabilities_cache
    _oracle_client_cache = None
    _driver_capabilities_cache = None


def _cached_record(
    cache: tuple[float, dict[str, Any]] | None,
    loader,
) -> tuple[dict[str, Any], tuple[float, dict[str, Any]]]:
    now = time.monotonic()
    if cache is not None and now - cache[0] < CACHE_TTL_SECONDS:
        return dict(cache[1]), cache
    value = loader()
    next_cache = (now, dict(value))
    return dict(value), next_cache


def get_oracle_client_config_record() -> dict[str, Any]:
    global _oracle_client_cache
    value, _oracle_client_cache = _cached_record(
        _oracle_client_cache,
        db_manager.discover_oracle_client_lib_dir,
    )
    return value


def get_database_driver_capabilities_record() -> dict[str, Any]:
    global _driver_capabilities_cache
    value, _driver_capabilities_cache = _cached_record(
        _driver_capabilities_cache,
        db_manager.get_database_driver_capabilities,
    )
    return value
