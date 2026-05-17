from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core import memory as memory_module
from core.alert_events import alert_summary, list_alert_events
from core.cron_manager import CronManager
from core.dashboard_metrics import build_alert_trend, build_dashboard_overview, build_risk_ranking
from core.inspection_results import run_summary, run_trend
from core.session_history import list_session_run_trace_events, summarize_session_run_trace_audit


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def build_dashboard_overview_payload(
    active_sessions: Mapping[str, dict],
    memory_db: Any | None = None,
) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    assets = store.get_all_assets()
    overview = build_dashboard_overview(
        assets,
        list(active_sessions.values()),
        CronManager.get_all_jobs(),
        alert_summary(),
        run_summary(),
    )
    overview["run_trace_audit"] = build_run_trace_audit_overview(active_sessions, memory_db=store)
    return overview


def build_run_trace_audit_overview(
    active_sessions: Mapping[str, dict],
    *,
    memory_db: Any | None = None,
    per_session_limit: int = 200,
) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    overview: dict[str, Any] = {
        "session_count": len(active_sessions),
        "sessions_with_trace": 0,
        "sessions_with_audit": 0,
        "sessions_with_gaps": 0,
        "session_errors": 0,
        "run_count": 0,
        "event_count": 0,
        "audited_run_count": 0,
        "unaudited_run_count": 0,
        "context_sources": 0,
        "context_hits": 0,
        "context_errors": 0,
        "prompt_modules": 0,
        "runtime_tool_count": 0,
        "runtime_success_count": 0,
        "runtime_error_count": 0,
        "runtime_timeout_count": 0,
        "runtime_retry_count": 0,
        "runtime_concurrent_count": 0,
        "runtime_untracked_count": 0,
        "source_counts": {},
        "module_counts": {},
        "runtime_error_types": {},
        "sessions": [],
    }
    for session_id, session_data in list(active_sessions.items()):
        info = session_data.get("info") if isinstance(session_data, Mapping) else {}
        if not isinstance(info, Mapping):
            info = {}
        try:
            events = list_session_run_trace_events(store, session_id, limit=per_session_limit)
            summary = summarize_session_run_trace_audit(events)
        except Exception:
            overview["session_errors"] += 1
            continue
        if summary["run_count"] > 0:
            overview["sessions_with_trace"] += 1
        if summary["audited_run_count"] > 0:
            overview["sessions_with_audit"] += 1
        if summary["unaudited_run_count"] > 0:
            overview["sessions_with_gaps"] += 1
        for key in (
            "run_count",
            "event_count",
            "audited_run_count",
            "unaudited_run_count",
            "context_sources",
            "context_hits",
            "context_errors",
            "prompt_modules",
            "runtime_tool_count",
            "runtime_success_count",
            "runtime_error_count",
            "runtime_timeout_count",
            "runtime_retry_count",
            "runtime_concurrent_count",
            "runtime_untracked_count",
        ):
            overview[key] += summary[key]
        _merge_count_map(overview["source_counts"], summary.get("source_counts") or {})
        _merge_count_map(overview["module_counts"], summary.get("module_counts") or {})
        _merge_flat_count_map(overview["runtime_error_types"], summary.get("runtime_error_types") or {})
        if summary["run_count"] > 0 or summary["unaudited_run_count"] > 0:
            overview["sessions"].append(
                {
                    "session_id": session_id,
                    "label": info.get("remark") or info.get("host") or session_id,
                    "host": info.get("host") or "",
                    "protocol": info.get("protocol") or "",
                    "group_name": (info.get("tags") or [""])[0] if isinstance(info.get("tags"), list) else "",
                    "run_count": summary["run_count"],
                    "audited_run_count": summary["audited_run_count"],
                    "unaudited_run_count": summary["unaudited_run_count"],
                    "context_errors": summary["context_errors"],
                    "runtime_tool_count": summary["runtime_tool_count"],
                    "runtime_error_count": summary["runtime_error_count"],
                    "runtime_timeout_count": summary["runtime_timeout_count"],
                    "runtime_retry_count": summary["runtime_retry_count"],
                }
            )
    overview["sessions"] = sorted(
        overview["sessions"],
        key=lambda item: (item["unaudited_run_count"], item["context_errors"], item["run_count"]),
        reverse=True,
    )[:8]
    return overview


def _merge_count_map(target: dict[str, dict[str, int]], source: Mapping[str, Mapping[str, int]]) -> None:
    for key, counts in source.items():
        if not isinstance(counts, Mapping):
            continue
        target_counts = target.setdefault(str(key), {})
        for count_key, value in counts.items():
            try:
                target_counts[str(count_key)] = target_counts.get(str(count_key), 0) + int(value or 0)
            except (TypeError, ValueError):
                continue


def _merge_flat_count_map(target: dict[str, int], source: Mapping[str, int]) -> None:
    for key, value in source.items():
        try:
            target[str(key)] = target.get(str(key), 0) + int(value or 0)
        except (TypeError, ValueError):
            continue


def build_dashboard_alert_trend_payload(limit: int = 5000) -> dict[str, Any]:
    return {"points": build_alert_trend(list_alert_events(limit=limit))}


def build_dashboard_risk_ranking_payload(limit: int = 5000) -> dict[str, Any]:
    return {"ranking": build_risk_ranking(list_alert_events(limit=limit))}


def build_dashboard_inspection_run_trend_payload() -> dict[str, Any]:
    return {"points": run_trend()}
