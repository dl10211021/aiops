from __future__ import annotations

from typing import Any

from core.alert_events import get_alert_event, list_alert_events, update_alert_event


class AlertEventServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_alert_event_records(
    *,
    status: str | None = None,
    severity: str | None = None,
    host: str | None = None,
    source_family: str | None = None,
    automation_mode: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    return list_alert_events(
        status=status,
        severity=severity,
        host=host,
        source_family=source_family,
        automation_mode=automation_mode,
        limit=limit,
    )


def get_alert_event_record(alert_id: str) -> dict[str, Any]:
    alert = get_alert_event(alert_id)
    if not alert:
        raise AlertEventServiceError(404, "告警事件不存在")
    return alert


def update_alert_event_record(
    alert_id: str,
    *,
    status: str | None = None,
    assignee: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    try:
        alert = update_alert_event(alert_id, status=status, assignee=assignee, note=note)
    except ValueError as exc:
        raise AlertEventServiceError(422, str(exc)) from exc
    if not alert:
        raise AlertEventServiceError(404, "告警事件不存在")
    return alert
