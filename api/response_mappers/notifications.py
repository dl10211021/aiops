from __future__ import annotations

from typing import Any


def notification_config_response_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": config,
    }


def notification_config_saved_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "告警通道配置已保存并生效",
    }


def notification_channel_test_response_kwargs(message: str) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }
