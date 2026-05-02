from __future__ import annotations

from collections.abc import Callable, Mapping

from core import app_config_service
from core.notification_config import save_notification_config


def _resolve_persist(persist: Callable[[dict[str, str]], None] | None = None) -> Callable[[dict[str, str]], None]:
    return persist if persist is not None else app_config_service.update_env_file_values


def save_notification_config_record(
    config: Mapping[str, object],
    *,
    persist: Callable[[dict[str, str]], None] | None = None,
) -> dict[str, str]:
    return save_notification_config(config, persist=_resolve_persist(persist))
