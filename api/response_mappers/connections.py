from __future__ import annotations

from typing import Any


def session_closed_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "Connection closed safely",
    }


def legacy_command_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }
