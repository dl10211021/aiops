from __future__ import annotations

from typing import Any


def inspection_response_status(report: dict[str, Any]) -> str:
    status = report.get("status")
    if status in {"success", "warning"}:
        return "success"
    return status or "error"


def inspection_response_message(report: dict[str, Any]) -> str:
    return report.get("summary") or report.get("message", "")


def build_inspection_response_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": inspection_response_status(report),
        "message": inspection_response_message(report),
        "data": {"inspection": report},
    }
