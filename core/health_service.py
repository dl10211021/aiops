from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import Any, Callable

from core.hydration_status_service import get_hydrate_status_record


HealthPayload = dict[str, Any]
HydrateStatusGetter = Callable[[], dict[str, Any]]


def build_health_status(
    *,
    base_path: str,
    root_dir: str,
    version: str,
    hydrate_status_getter: HydrateStatusGetter = get_hydrate_status_record,
) -> HealthPayload:
    db_path = os.path.join(root_dir, "opscore.db")
    cron_db_path = os.path.join(root_dir, "cron_jobs.sqlite")
    react_index = os.path.join(base_path, "static_react", "index.html")

    checks: dict[str, dict[str, Any]] = {
        "database": {"status": "ok", "path": "opscore.db"},
        "cron_store": {"status": "ok", "path": "cron_jobs.sqlite"},
        "storage": {"status": "ok", "path": root_dir},
        "frontend": {"status": "ok" if os.path.exists(react_index) else "warning"},
        "hydrate": hydrate_status_getter(),
    }

    try:
        with closing(sqlite3.connect(db_path, timeout=2)) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        checks["database"] = {"status": "error", "path": "opscore.db", "error": str(exc)}

    try:
        if os.path.exists(cron_db_path):
            with closing(sqlite3.connect(cron_db_path, timeout=2)) as conn:
                conn.execute("SELECT 1")
        else:
            checks["cron_store"] = {
                "status": "ok",
                "path": "cron_jobs.sqlite",
                "message": "not initialized",
            }
    except Exception as exc:
        checks["cron_store"] = {"status": "error", "path": "cron_jobs.sqlite", "error": str(exc)}

    if not os.access(root_dir, os.W_OK):
        checks["storage"] = {"status": "error", "path": root_dir, "error": "not writable"}

    overall = "ok"
    if any(item.get("status") == "error" for item in checks.values()):
        overall = "error"
    elif any(item.get("status") == "warning" for item in checks.values()):
        overall = "warning"

    return {
        "status": overall,
        "service": "opscore-aiops",
        "version": version,
        "checks": checks,
    }
