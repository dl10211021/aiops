from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core import memory as memory_module
from core.alert_events import alert_summary, list_alert_events
from core.cron_manager import CronManager
from core.dashboard_metrics import build_alert_trend, build_dashboard_overview, build_risk_ranking
from core.inspection_results import run_summary, run_trend


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def build_dashboard_overview_payload(
    active_sessions: Mapping[str, dict],
    memory_db: Any | None = None,
) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    assets = store.get_all_assets()
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
