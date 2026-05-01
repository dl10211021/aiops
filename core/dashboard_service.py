from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.alert_events import alert_summary, list_alert_events
from core.cron_manager import CronManager
from core.dashboard_metrics import build_alert_trend, build_dashboard_overview, build_risk_ranking
from core.inspection_results import run_summary, run_trend


def build_dashboard_overview_payload(
    memory_db,
    active_sessions: Mapping[str, dict],
) -> dict[str, Any]:
    assets = memory_db.get_all_assets()
    return build_dashboard_overview(
        assets,
        list(active_sessions.values()),
        CronManager.get_all_jobs(),
        alert_summary(),
        run_summary(),
    )


def build_dashboard_alert_trend_payload(limit: int = 5000) -> dict[str, Any]:
    return {"points": build_alert_trend(list_alert_events(limit=limit))}


def build_dashboard_risk_ranking_payload(limit: int = 5000) -> dict[str, Any]:
    return {"ranking": build_risk_ranking(list_alert_events(limit=limit))}


def build_dashboard_inspection_run_trend_payload() -> dict[str, Any]:
    return {"points": run_trend()}
