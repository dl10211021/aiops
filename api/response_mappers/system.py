from __future__ import annotations

from typing import Any


def dashboard_response_kwargs(data: Any) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def system_info_response_kwargs(data: Any) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }
