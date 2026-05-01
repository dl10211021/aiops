from __future__ import annotations

from core.asset_protocols import resolve_asset_identity


def summarize_assets_by_identity(assets: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    by_protocol: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for asset in assets:
        identity = resolve_asset_identity(
            asset.get("asset_type"),
            asset.get("protocol"),
            asset.get("extra_args", {}),
            asset.get("host"),
            asset.get("port"),
            asset.get("remark"),
        )
        category = identity.get("category") or "other"
        by_category[category] = by_category.get(category, 0) + 1
        by_protocol[identity["protocol"]] = by_protocol.get(identity["protocol"], 0) + 1
        by_type[identity["asset_type"]] = by_type.get(identity["asset_type"], 0) + 1
    return {
        "by_category": by_category,
        "by_protocol": by_protocol,
        "by_type": by_type,
    }


def summarize_active_sessions_by_protocol(active_sessions: list[dict]) -> dict[str, int]:
    active_by_protocol: dict[str, int] = {}
    for item in active_sessions:
        info = item.get("info", {})
        protocol = resolve_asset_identity(
            info.get("asset_type"),
            info.get("protocol"),
            info.get("extra_args", {}),
            info.get("host"),
            info.get("port"),
            info.get("remark"),
        )["protocol"]
        active_by_protocol[protocol] = active_by_protocol.get(protocol, 0) + 1
    return active_by_protocol


def summarize_jobs(jobs: list[dict]) -> dict[str, int]:
    return {
        "total": len(jobs),
        "scheduled": sum(1 for job in jobs if job.get("status") == "scheduled"),
        "paused": sum(1 for job in jobs if job.get("status") == "paused"),
    }


def build_dashboard_overview(
    assets: list[dict],
    active_sessions: list[dict],
    jobs: list[dict],
    alerts: dict,
    inspection_runs: dict,
) -> dict:
    asset_summary = summarize_assets_by_identity(assets)
    active_by_protocol = summarize_active_sessions_by_protocol(active_sessions)
    by_category = asset_summary["by_category"]
    by_protocol = asset_summary["by_protocol"]
    return {
        "summary": {
            "asset_total": len(assets),
            "active_sessions": len(active_sessions),
            "asset_categories": len(by_category),
            "protocols": len(by_protocol),
        },
        **asset_summary,
        "active_by_protocol": active_by_protocol,
        "alerts": alerts,
        "jobs": summarize_jobs(jobs),
        "inspection_runs": inspection_runs,
    }


def build_alert_trend(alerts: list[dict]) -> list[dict]:
    buckets: dict[str, dict[str, int]] = {}
    for alert in alerts:
        day = str(alert.get("created_at") or "")[:10] or "unknown"
        severity = str(alert.get("severity") or "unknown").lower()
        bucket = buckets.setdefault(day, {"date": day, "total": 0})
        bucket["total"] += 1
        bucket[severity] = bucket.get(severity, 0) + 1
    return [buckets[key] for key in sorted(buckets)]


def build_risk_ranking(alerts: list[dict], limit: int = 20) -> list[dict[str, int | str]]:
    weights = {"critical": 5, "fatal": 5, "error": 4, "warning": 2, "warn": 2, "info": 1}
    by_host: dict[str, dict[str, int | str]] = {}
    for alert in alerts:
        host = str(alert.get("host") or "unknown")
        severity = str(alert.get("severity") or "info").lower()
        item = by_host.setdefault(host, {"host": host, "count": 0, "score": 0})
        item["count"] = int(item["count"]) + 1
        item["score"] = int(item["score"]) + weights.get(severity, 1)
    return sorted(
        by_host.values(),
        key=lambda item: (int(item["score"]), int(item["count"])),
        reverse=True,
    )[:limit]
