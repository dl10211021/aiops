"""Persistent inspection run history for scheduled AIOps jobs."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
INSPECTION_RUN_STORE_PATH = ROOT_DIR / "inspection_runs.json"
_LOCK = threading.Lock()
SECRET_PATTERNS = [
    re.compile(r"managed-secret", re.IGNORECASE),
    re.compile(r"secret-key", re.IGNORECASE),
    re.compile(r"(password|api[_-]?key|token|secret)\s*[:=]\s*[^,\s}]+", re.IGNORECASE),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at: str | None, completed_at: str | None) -> int:
    start = _parse_time(started_at)
    end = _parse_time(completed_at)
    if not start or not end:
        return 0
    return max(0, int((end - start).total_seconds() * 1000))


def _load() -> list[dict[str, Any]]:
    if not INSPECTION_RUN_STORE_PATH.exists():
        return []
    try:
        with INSPECTION_RUN_STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    INSPECTION_RUN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = INSPECTION_RUN_STORE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    tmp_path.replace(INSPECTION_RUN_STORE_PATH)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub(lambda m: m.group(1) + "=********" if m.lastindex else "********", redacted)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in {"password", "api_key", "api_token", "token", "secret", "kubeconfig", "community_string"}:
                safe[key] = "********"
            else:
                safe[key] = _redact(item)
        return safe
    return value


def record_run(
    *,
    job_id: str,
    status: str,
    target_scope: str,
    scope_value: str | None,
    message: str,
    targets: list[dict[str, Any]],
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    started = started_at or _now()
    completed = completed_at or _now()
    run = {
        "id": f"run_{uuid.uuid4().hex[:12]}",
        "job_id": job_id,
        "status": status,
        "target_scope": target_scope,
        "scope_value": scope_value,
        "message": message,
        "target_count": len(targets),
        "targets": targets,
        "started_at": started,
        "completed_at": completed,
        "duration_ms": _duration_ms(started, completed),
    }
    with _LOCK:
        items = _load()
        items.insert(0, run)
        _save(items[:1000])
    return run


def _filter_run_targets_by_asset(run: dict[str, Any], asset_id: int | None = None) -> dict[str, Any]:
    item = dict(run)
    targets = list(item.get("targets") or [])
    if asset_id is not None:
        targets = [target for target in targets if target.get("asset_id") == asset_id]
        item["target_count"] = len(targets)
    item["targets"] = targets
    return _redact(item)


def list_runs(job_id: str | None = None, limit: int = 50, asset_id: int | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        items = _load()
    if job_id:
        items = [item for item in items if item.get("job_id") == job_id]
    if asset_id is not None:
        items = [
            _filter_run_targets_by_asset(item, asset_id)
            for item in items
            if any(target.get("asset_id") == asset_id for target in item.get("targets") or [])
        ]
    else:
        items = [_redact(item) for item in items]
    return items[: max(1, min(int(limit or 50), 500))]


def get_run(run_id: str) -> dict[str, Any] | None:
    with _LOCK:
        for item in _load():
            if item.get("id") == run_id:
                return _redact(item)
    return None


def build_report(run_id: str) -> dict[str, Any] | None:
    run = get_run(run_id)
    if not run:
        return None
    targets = run.get("targets") or []
    success_count = sum(1 for target in targets if target.get("status") == "success")
    error_count = sum(1 for target in targets if target.get("status") == "error")
    return {
        "run_id": run.get("id"),
        "job_id": run.get("job_id"),
        "status": run.get("status"),
        "target_scope": run.get("target_scope"),
        "scope_value": run.get("scope_value"),
        "message": run.get("message"),
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "summary": {
            "target_count": len(targets),
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": round((success_count / len(targets)) * 100, 2) if targets else 0.0,
        },
        "targets": targets,
    }


def export_report_markdown(run_id: str) -> str | None:
    report = build_report(run_id)
    if not report:
        return None
    summary = report["summary"]
    lines = [
        "# 巡检报告",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Job ID: `{report['job_id']}`",
        f"- 状态: `{report['status']}`",
        f"- 范围: `{report['target_scope']}` / `{report.get('scope_value') or '-'}`",
        f"- 开始: `{report.get('started_at') or '-'}`",
        f"- 完成: `{report.get('completed_at') or '-'}`",
        "",
        "## 摘要",
        "",
        f"- 目标数: {summary['target_count']}",
        f"- 成功: {summary['success_count']}",
        f"- 失败: {summary['error_count']}",
        f"- 成功率: {summary['success_rate']}%",
        "",
        "## 目标结果",
        "",
    ]
    for target in report["targets"]:
        lines.extend(
            [
                f"### {target.get('host') or '-'}",
                "",
                f"- 资产ID: `{target.get('asset_id') or '-'}`",
                f"- 类型/协议: `{target.get('asset_type') or '-'}` / `{target.get('protocol') or '-'}`",
                f"- 状态: `{target.get('status') or '-'}`",
            ]
        )
        if target.get("error"):
            lines.append(f"- 错误: `{target.get('error')}`")
        if target.get("result"):
            lines.extend(["", "```text", str(target.get("result"))[:4000], "```"])
        lines.append("")
    return "\n".join(lines)


def run_summary(limit: int = 5000) -> dict[str, Any]:
    runs = list_runs(limit=limit)
    total = len(runs)
    completed = sum(1 for run in runs if run.get("status") == "completed")
    failed = sum(1 for run in runs if run.get("status") == "failed")
    partial = sum(1 for run in runs if run.get("status") == "partial")
    empty = sum(1 for run in runs if run.get("status") == "empty")
    success_rate = round((completed / total) * 100, 2) if total else 0.0
    targets_total = 0
    targets_success = 0
    targets_error = 0
    for run in runs:
        targets = run.get("targets") or []
        targets_total += len(targets)
        targets_success += sum(1 for target in targets if target.get("status") == "success")
        targets_error += sum(1 for target in targets if target.get("status") == "error")
    recent_failures = [
        run
        for run in runs
        if run.get("status") in {"failed", "partial"}
    ][:10]
    return {
        "total_runs": total,
        "completed": completed,
        "failed": failed,
        "partial": partial,
        "empty": empty,
        "success_rate": success_rate,
        "targets_total": targets_total,
        "targets_success": targets_success,
        "targets_error": targets_error,
        "recent_failures": recent_failures,
    }


def run_trend(limit: int = 5000) -> list[dict[str, Any]]:
    runs = list_runs(limit=limit)
    buckets: dict[str, dict[str, Any]] = {}
    for run in runs:
        day = str(run.get("completed_at") or run.get("started_at") or "")[:10] or "unknown"
        bucket = buckets.setdefault(
            day,
            {
                "date": day,
                "total_runs": 0,
                "completed": 0,
                "failed": 0,
                "partial": 0,
                "empty": 0,
                "target_success": 0,
                "target_error": 0,
                "duration_ms_total": 0,
            },
        )
        status = str(run.get("status") or "unknown")
        bucket["total_runs"] += 1
        if status in {"completed", "failed", "partial", "empty"}:
            bucket[status] += 1
        bucket["duration_ms_total"] += int(run.get("duration_ms") or 0)
        for target in run.get("targets") or []:
            if target.get("status") == "success":
                bucket["target_success"] += 1
            elif target.get("status") == "error":
                bucket["target_error"] += 1

    points = []
    for day in sorted(buckets):
        bucket = buckets[day]
        total = int(bucket["total_runs"])
        completed = int(bucket["completed"])
        bucket["success_rate"] = round((completed / total) * 100, 2) if total else 0.0
        bucket["avg_duration_ms"] = round(int(bucket["duration_ms_total"]) / total, 2) if total else 0.0
        bucket.pop("duration_ms_total", None)
        points.append(bucket)
    return points
