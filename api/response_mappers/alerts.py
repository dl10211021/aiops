from __future__ import annotations

from typing import Any

from api.schema_models.alerts import AlertEventUpdateRequest


def alert_event_list_query_kwargs(
    status: str | None,
    severity: str | None,
    host: str | None,
    source_family: str | None,
    automation_mode: str | None,
    limit: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "severity": severity,
        "host": host,
        "source_family": source_family,
        "automation_mode": automation_mode,
        "limit": limit,
    }


def alert_event_update_kwargs(req: AlertEventUpdateRequest) -> dict[str, Any]:
    return {
        "status": req.status,
        "assignee": req.assignee,
        "note": req.note,
    }


def alert_events_response_kwargs(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"alerts": alerts},
    }


def alert_event_response_kwargs(alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"alert": alert},
    }


def alert_webhook_response_kwargs(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": result["message"],
        "data": result["data"],
    }
