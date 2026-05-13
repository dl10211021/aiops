"""Persistent inspection run history for scheduled AIOps jobs."""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from html import escape
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
INSPECTION_RUN_STORE_PATH = ROOT_DIR / "inspection_runs.json"
_LOCK = threading.Lock()
_RUN_STORE_CACHE: tuple[str, float, int, list[dict[str, Any]]] | None = None
_SAVE_REPLACE_ATTEMPTS = 5
_SAVE_REPLACE_RETRY_DELAY_SECONDS = 0.05
SECRET_PATTERNS = [
    re.compile(r"managed-secret", re.IGNORECASE),
    re.compile(r"secret-key", re.IGNORECASE),
    re.compile(r"(password|api[_-]?key|token|secret)\s*[:=]\s*[^,\s}]+", re.IGNORECASE),
]
SCORE_PROFILES = {
    "linux": {
        "label": "Linux 主机",
        "dimensions": [
            ("availability", "可用性", 0.30),
            ("capacity", "容量", 0.25),
            ("performance", "性能", 0.20),
            ("security", "安全", 0.15),
            ("maintenance", "可维护性", 0.10),
        ],
    },
    "windows": {
        "label": "Windows 主机",
        "dimensions": [
            ("availability", "可用性", 0.30),
            ("capacity", "容量", 0.20),
            ("performance", "性能", 0.20),
            ("security", "安全", 0.20),
            ("maintenance", "服务状态", 0.10),
        ],
    },
    "database": {
        "label": "数据库",
        "dimensions": [
            ("availability", "可用性", 0.25),
            ("capacity", "容量", 0.25),
            ("performance", "性能", 0.20),
            ("consistency", "一致性", 0.15),
            ("backup", "备份恢复", 0.15),
        ],
    },
    "oracle": {
        "label": "Oracle 数据库",
        "dimensions": [
            ("availability", "可用性", 0.25),
            ("capacity", "表空间/归档", 0.25),
            ("performance", "性能", 0.20),
            ("consistency", "一致性", 0.15),
            ("backup", "备份恢复", 0.15),
        ],
    },
    "network": {
        "label": "网络设备",
        "dimensions": [
            ("availability", "可用性", 0.35),
            ("performance", "链路性能", 0.25),
            ("errors", "错误包/丢包", 0.20),
            ("capacity", "容量", 0.10),
            ("security", "安全", 0.10),
        ],
    },
    "default": {
        "label": "通用系统",
        "dimensions": [
            ("availability", "可用性", 0.35),
            ("capacity", "容量", 0.20),
            ("performance", "性能", 0.20),
            ("security", "安全", 0.15),
            ("maintenance", "可维护性", 0.10),
        ],
    },
}


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
    global _RUN_STORE_CACHE
    if not INSPECTION_RUN_STORE_PATH.exists():
        _RUN_STORE_CACHE = None
        return []
    try:
        stat = INSPECTION_RUN_STORE_PATH.stat()
        cache_path = str(INSPECTION_RUN_STORE_PATH)
        if _RUN_STORE_CACHE and _RUN_STORE_CACHE[0] == cache_path and _RUN_STORE_CACHE[1] == stat.st_mtime and _RUN_STORE_CACHE[2] == stat.st_size:
            return [dict(item) for item in _RUN_STORE_CACHE[3]]
    except OSError:
        return []
    try:
        with INSPECTION_RUN_STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        items = [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
        stat = INSPECTION_RUN_STORE_PATH.stat()
        _RUN_STORE_CACHE = (str(INSPECTION_RUN_STORE_PATH), stat.st_mtime, stat.st_size, [dict(item) for item in items])
        return items
    except (OSError, json.JSONDecodeError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    global _RUN_STORE_CACHE
    INSPECTION_RUN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = INSPECTION_RUN_STORE_PATH.with_name(
        f"{INSPECTION_RUN_STORE_PATH.name}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        _replace_store_file(tmp_path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
    _RUN_STORE_CACHE = None


def _replace_store_file(tmp_path: Path) -> None:
    for attempt in range(_SAVE_REPLACE_ATTEMPTS):
        try:
            tmp_path.replace(INSPECTION_RUN_STORE_PATH)
            return
        except PermissionError:
            if attempt == _SAVE_REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_SAVE_REPLACE_RETRY_DELAY_SECONDS * (attempt + 1))


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


def _score_grade(score: int) -> tuple[str, str]:
    if score >= 90:
        return ("A", "优秀")
    if score >= 80:
        return ("B", "良好")
    if score >= 70:
        return ("C", "关注")
    if score >= 60:
        return ("D", "风险")
    return ("E", "严重")


def _score_profile_for_target(target: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    text = f"{target.get('asset_type') or ''} {target.get('protocol') or ''}".lower()
    if "oracle" in text:
        return "oracle", SCORE_PROFILES["oracle"]
    if any(token in text for token in ("mysql", "postgres", "pgsql", "mongodb", "mongo", "tidb", "redis", "database", "db2", "sqlserver", "mssql", "数据库")):
        return "database", SCORE_PROFILES["database"]
    if any(token in text for token in ("windows", "winrm")):
        return "windows", SCORE_PROFILES["windows"]
    if any(token in text for token in ("switch", "router", "firewall", "snmp", "network", "h3c", "cisco", "huawei", "交换机", "路由", "防火墙")):
        return "network", SCORE_PROFILES["network"]
    if any(token in text for token in ("linux", "ssh", "unix")):
        return "linux", SCORE_PROFILES["linux"]
    return "default", SCORE_PROFILES["default"]


def _target_score_text(target: dict[str, Any]) -> str:
    return " ".join(
        str(value or "")
        for value in (
            target.get("status"),
            target.get("error"),
            target.get("result"),
            target.get("message"),
            target.get("asset_type"),
            target.get("protocol"),
        )
    ).lower()[:12000]


def _explicit_health_score(text: str) -> int | None:
    match = re.search(r"(?:总体健康评分|健康评分|巡检评分|评分)\s*[:：]\s*(\d{1,3})\s*/\s*100", text, re.IGNORECASE)
    if not match:
        return None
    return max(0, min(100, int(match.group(1))))


def _score_dimension_id(profile: dict[str, Any], preferred: str) -> str:
    ids = {item[0] for item in profile["dimensions"]}
    if preferred in ids:
        return preferred
    if preferred == "backup" and "maintenance" in ids:
        return "maintenance"
    if preferred == "consistency" and "maintenance" in ids:
        return "maintenance"
    if preferred == "errors" and "performance" in ids:
        return "performance"
    return "availability"


def _add_score_deduction(
    dimensions: dict[str, dict[str, Any]],
    deductions: list[dict[str, Any]],
    dimension_id: str,
    points: int,
    reason: str,
) -> None:
    if dimension_id == "overall":
        for dimension in dimensions.values():
            dimension["score"] = max(0, int(dimension["score"]) - points)
        deductions.append(
            {"dimension": "overall", "label": "整体", "points": points, "reason": reason}
        )
        return
    dimension = dimensions.get(dimension_id)
    if not dimension:
        return
    dimension["score"] = max(0, int(dimension["score"]) - points)
    deductions.append(
        {
            "dimension": dimension_id,
            "label": dimension["label"],
            "points": points,
            "reason": reason,
        }
    )


def _apply_keyword_deduction(
    text: str,
    profile: dict[str, Any],
    dimensions: dict[str, dict[str, Any]],
    deductions: list[dict[str, Any]],
    tokens: tuple[str, ...],
    dimension_id: str,
    points: int,
    reason: str,
) -> None:
    if any(token in text for token in tokens):
        _add_score_deduction(
            dimensions,
            deductions,
            _score_dimension_id(profile, dimension_id),
            points,
            reason,
        )


def _score_target(target: dict[str, Any]) -> dict[str, Any]:
    profile_id, profile = _score_profile_for_target(target)
    dimensions = {
        dimension_id: {
            "id": dimension_id,
            "label": label,
            "weight": weight,
            "score": 100,
        }
        for dimension_id, label, weight in profile["dimensions"]
    }
    deductions: list[dict[str, Any]] = []
    status = str(target.get("status") or "").lower()
    text = _target_score_text(target)
    explicit_score = _explicit_health_score(text)

    if status in {"error", "failed", "failure"}:
        _add_score_deduction(dimensions, deductions, "overall", 45, "巡检目标执行失败")
    elif status in {"cancelled", "canceled"}:
        _add_score_deduction(dimensions, deductions, "overall", 35, "巡检目标被取消")
    elif status in {"running", "pending"}:
        _add_score_deduction(dimensions, deductions, "overall", 20, "巡检目标仍在运行或等待")
    elif status and status not in {"success", "completed", "ok"}:
        _add_score_deduction(dimensions, deductions, "overall", 15, "巡检目标状态未确认")

    _apply_keyword_deduction(text, profile, dimensions, deductions, ("timeout", "timed out", "超时"), "availability", 18, "连接或执行超时")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("connection refused", "unreachable", "无法连接", "连接失败", "拒绝连接"), "availability", 18, "连接不可达")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("authentication failed", "auth failed", "invalid password", "permission denied", "unauthorized", "forbidden", "认证失败", "登录失败", "权限拒绝"), "security", 16, "认证或权限异常")
    if explicit_score is not None and explicit_score < 100:
        _add_score_deduction(dimensions, deductions, "overall", 100 - explicit_score, "巡检报告给出显式健康评分")

    _apply_keyword_deduction(text, profile, dimensions, deductions, ("disk full", "filesystem full", "no space", "space full", "free space low", "usage 9", "磁盘满", "空间不足", "利用率高", "使用率高", "表空间不足", "表空间高", "需立即扩容", "需要扩容", "建议扩容"), "capacity", 14, "容量使用存在风险")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("slow", "latency", "delay", "高延迟", "响应慢", "慢查询"), "performance", 12, "性能或响应时延异常")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("packet loss", "crc", "drop", "discard", "丢包", "错包"), "errors", 12, "链路错误或丢包")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("deadlock", "lock wait", "blocked", "锁等待", "死锁", "阻塞"), "consistency", 12, "锁等待或一致性风险")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("no backup", "backup missing", "rman", "归档", "redo", "archive", "无任何备份", "未配置备份", "没有备份"), "backup", 10, "备份恢复或归档需关注")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("ora-00257", "archiver stuck", "archive log full", "归档满"), "capacity", 25, "Oracle 归档或表空间高风险")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("ora-", "critical", "fatal", "panic", "宕机", "严重", "不可用"), "availability", 16, "发现严重错误信号")
    _apply_keyword_deduction(text, profile, dimensions, deductions, ("warning:", "alert:", "failed:", "error:", "存在告警", "发现告警", "发现异常", "执行失败"), "availability", 8, "存在告警或异常文本")

    weighted_score = 0.0
    for dimension in dimensions.values():
        weighted_score += int(dimension["score"]) * float(dimension["weight"])
    score = max(0, min(100, int(round(weighted_score))))
    grade, grade_label = _score_grade(score)
    return {
        "target": {
            "asset_id": target.get("asset_id"),
            "host": target.get("host"),
            "asset_type": target.get("asset_type"),
            "protocol": target.get("protocol"),
        },
        "status": target.get("status"),
        "profile": profile_id,
        "profile_label": profile["label"],
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "dimensions": list(dimensions.values()),
        "deductions": deductions[:12],
    }


def _build_inspection_score(run: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    if not targets:
        return {
            "score": 0,
            "grade": "N",
            "grade_label": "无目标",
            "profile": "none",
            "profile_label": "无目标",
            "dimensions": [],
            "target_scores": [],
            "deductions": [],
        }

    target_scores = [_score_target(target) for target in targets]
    score = int(round(sum(item["score"] for item in target_scores) / len(target_scores)))
    grade, grade_label = _score_grade(score)
    profile_counts: dict[str, int] = {}
    profile_labels: dict[str, str] = {}
    dimension_totals: dict[str, dict[str, Any]] = {}
    deductions: list[dict[str, Any]] = []

    for item in target_scores:
        profile_counts[item["profile"]] = profile_counts.get(item["profile"], 0) + 1
        profile_labels[item["profile"]] = item["profile_label"]
        host = (item.get("target") or {}).get("host") or "-"
        for dimension in item["dimensions"]:
            bucket = dimension_totals.setdefault(
                dimension["id"],
                {"id": dimension["id"], "label": dimension["label"], "score_total": 0, "count": 0},
            )
            bucket["score_total"] += int(dimension["score"])
            bucket["count"] += 1
        for deduction in item["deductions"][:4]:
            deductions.append({"host": host, **deduction})

    dimensions = [
        {
            "id": item["id"],
            "label": item["label"],
            "score": int(round(item["score_total"] / max(1, item["count"]))),
        }
        for item in dimension_totals.values()
    ]
    dimensions.sort(key=lambda item: item["score"])
    if len(profile_counts) == 1:
        profile = next(iter(profile_counts))
        profile_label = profile_labels.get(profile, profile)
    else:
        profile = "mixed"
        profile_label = "混合系统"

    return {
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "profile": profile,
        "profile_label": profile_label,
        "dimensions": dimensions,
        "target_scores": target_scores,
        "deductions": deductions[:10],
        "run_status": run.get("status"),
    }


def _completed_at_for_status(status: str, completed_at: str | None) -> str | None:
    if completed_at is not None:
        return completed_at
    if status == "running":
        return None
    return _now()


def record_run(
    *,
    job_id: str,
    status: str,
    target_scope: str,
    scope_value: str | None,
    message: str,
    targets: list[dict[str, Any]],
    events: list[dict[str, Any]] | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    started = started_at or _now()
    completed = _completed_at_for_status(status, completed_at)
    run = {
        "id": f"run_{uuid.uuid4().hex[:12]}",
        "job_id": job_id,
        "status": status,
        "target_scope": target_scope,
        "scope_value": scope_value,
        "message": message,
        "target_count": len(targets),
        "targets": targets,
        "events": events or [],
        "notification": None,
        "started_at": started,
        "completed_at": completed,
        "duration_ms": _duration_ms(started, completed),
    }
    with _LOCK:
        items = _load()
        items.insert(0, run)
        _save(items[:1000])
    return run


def update_run(run_id: str, **fields: Any) -> dict[str, Any] | None:
    with _LOCK:
        items = _load()
        for index, item in enumerate(items):
            if item.get("id") != run_id:
                continue
            updated = dict(item)
            updated.update(fields)
            if "targets" in fields:
                updated["target_count"] = len(updated.get("targets") or [])
            if "completed_at" in fields or "started_at" in fields:
                updated["duration_ms"] = _duration_ms(updated.get("started_at"), updated.get("completed_at"))
            items[index] = updated
            _save(items[:1000])
            return updated
    return None


def delete_run(run_id: str) -> bool:
    with _LOCK:
        items = _load()
        next_items = [item for item in items if item.get("id") != run_id]
        if len(next_items) == len(items):
            return False
        _save(next_items[:1000])
        return True


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


def _phase_status_for_targets(targets: list[dict[str, Any]], run_status: str) -> str:
    if not targets:
        return "skipped"
    if any(target.get("status") in {"pending", "running"} for target in targets):
        return "running"
    if all(target.get("status") == "success" for target in targets):
        return "completed"
    if any(target.get("status") == "success" for target in targets):
        return "partial"
    if run_status == "cancelled" or all(target.get("status") == "cancelled" for target in targets):
        return "cancelled"
    return "failed"


def _phase_status_for_notification(notification: dict[str, Any] | None, run_status: str) -> str:
    if not notification:
        return "pending" if run_status == "running" else "skipped"
    status = str(notification.get("status") or "").lower()
    if status in {"error", "failed", "failure"}:
        return "failed"
    if status in {"skipped", "disabled"}:
        return "skipped"
    return "completed"


def _first_event_time(events: list[dict[str, Any]], event_type: str) -> str | None:
    for event in events:
        if event.get("type") == event_type:
            return event.get("time")
    return None


def _last_event_time(events: list[dict[str, Any]], event_type: str) -> str | None:
    for event in reversed(events):
        if event.get("type") == event_type:
            return event.get("time")
    return None


def _build_run_trace(run: dict[str, Any], targets: list[dict[str, Any]]) -> dict[str, Any]:
    events = list(run.get("events") or [])
    notification = run.get("notification") if isinstance(run.get("notification"), dict) else None
    run_status = str(run.get("status") or "unknown")
    success_count = sum(1 for target in targets if target.get("status") == "success")
    error_count = sum(1 for target in targets if target.get("status") == "error")
    cancelled_count = sum(1 for target in targets if target.get("status") == "cancelled")
    started_at = run.get("started_at")
    completed_at = run.get("completed_at")
    return {
        "trace_id": f"inspection:{run.get('id')}",
        "kind": "inspection_run",
        "status": run_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": run.get("duration_ms") or _duration_ms(started_at, completed_at),
        "counters": {
            "events": len(events),
            "targets": len(targets),
            "success": success_count,
            "error": error_count,
            "cancelled": cancelled_count,
        },
        "phases": [
            {
                "id": "setup",
                "label": "创建运行记录",
                "status": "completed" if started_at or _first_event_time(events, "run_started") else "pending",
                "started_at": started_at or _first_event_time(events, "run_started"),
                "completed_at": _first_event_time(events, "run_started") or started_at,
                "detail": f"等待处理 {len(targets)} 个目标。",
            },
            {
                "id": "targets",
                "label": "目标巡检",
                "status": _phase_status_for_targets(targets, run_status),
                "started_at": _first_event_time(events, "target_started"),
                "completed_at": _last_event_time(events, "target_completed")
                or _last_event_time(events, "target_failed")
                or completed_at,
                "detail": f"成功 {success_count}，失败 {error_count}，取消 {cancelled_count}。",
            },
            {
                "id": "notification",
                "label": "通知发送",
                "status": _phase_status_for_notification(notification, run_status),
                "started_at": _last_event_time(events, "notification_completed"),
                "completed_at": _last_event_time(events, "notification_completed"),
                "detail": (notification or {}).get("message") or (notification or {}).get("status") or "未记录通知结果。",
            },
            {
                "id": "finalize",
                "label": "归档报告",
                "status": run_status,
                "started_at": _last_event_time(events, "run_completed") or completed_at,
                "completed_at": completed_at,
                "detail": run.get("message") or "",
            },
        ],
    }


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
        "notification": run.get("notification"),
        "events": run.get("events") or [],
        "trace": _build_run_trace(run, targets),
        "score": _build_inspection_score(run, targets),
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
    ]
    score = report.get("score") or {}
    if score:
        lines.extend(
            [
                "## 健康评分",
                "",
                f"- 总分: {score.get('score', 0)} / 100",
                f"- 等级: {score.get('grade_label') or score.get('grade') or '-'}",
                f"- 评分模型: {score.get('profile_label') or '-'}",
                "",
            ]
        )
        dimensions = score.get("dimensions") or []
        if dimensions:
            lines.append("### 维度")
            lines.append("")
            for dimension in dimensions:
                lines.append(
                    f"- {dimension.get('label') or dimension.get('id') or '-'}: {dimension.get('score', 0)}"
                )
            lines.append("")
        target_scores = score.get("target_scores") or []
        if target_scores:
            lines.append("### 目标评分")
            lines.append("")
            for target_score in target_scores:
                target = target_score.get("target") or {}
                lines.append(
                    f"- {target.get('host') or '-'}: {target_score.get('score', 0)} / 100，{target_score.get('grade_label') or '-'}，{target_score.get('profile_label') or '-'}"
                )
                for deduction in (target_score.get("deductions") or [])[:5]:
                    lines.append(
                        f"  - 扣分 {deduction.get('points', 0)}: {deduction.get('reason') or '-'}"
                    )
            lines.append("")
    notification = report.get("notification") or {}
    if notification:
        lines.extend(
            [
                "## 通知",
                "",
                f"- 状态: `{notification.get('status') or '-'}`",
                f"- 结果: `{notification.get('message') or '-'}`",
                "",
            ]
        )
    events = report.get("events") or []
    if events:
        lines.extend(["## 运行事件", ""])
        for event in events:
            lines.append(
                f"- `{event.get('time') or '-'}` {event.get('message') or event.get('type') or '-'}"
            )
        lines.append("")
    trace = report.get("trace") or {}
    phases = trace.get("phases") or []
    if phases:
        lines.extend(["## AIOps Run Trace", ""])
        lines.append(f"- Trace ID: `{trace.get('trace_id') or '-'}`")
        lines.append(f"- 耗时: `{trace.get('duration_ms') or 0}ms`")
        lines.append("")
        for phase in phases:
            lines.append(
                f"- `{phase.get('status') or '-'}` {phase.get('label') or phase.get('id') or '-'}: {phase.get('detail') or '-'}"
            )
        lines.append("")
    lines.extend(["## 目标结果", ""])
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


def _html_text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return escape(str(value), quote=True)


def _html_anchor(value: Any) -> str:
    anchor = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return anchor or "report"


def _report_anchor(run_id: str) -> str:
    return f"report-{_html_anchor(run_id)}"


def _score_class(score: Any) -> str:
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 0
    if value >= 80:
        return "good"
    if value >= 60:
        return "warn"
    return "bad"


def _html_metric(label: str, value: Any, tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return (
        f'<div class="metric{tone_class}">'
        f'<div class="metric-label">{_html_text(label)}</div>'
        f'<div class="metric-value">{_html_text(value)}</div>'
        "</div>"
    )


def _related_report_index_html(report: dict[str, Any], current_run_id: str) -> str:
    job_id = report.get("job_id")
    if not job_id:
        return '<div class="empty">暂无同计划历史报告</div>'
    related_runs = list_runs(job_id=str(job_id), limit=20)
    rows: list[str] = []
    for run in related_runs:
        run_id = str(run.get("id") or "")
        if not run_id:
            continue
        run_report = build_report(run_id) or {}
        run_score = (run_report.get("score") or {}).get("score")
        score_label = _html_text(run_score if run_score is not None else "-")
        status = run.get("status") or "-"
        current_class = " current" if run_id == current_run_id else ""
        current_badge = '<span class="badge">当前</span>' if run_id == current_run_id else ""
        anchor = _report_anchor(run_id)
        rows.append(
            f'<a class="report-row{current_class}" href="#{anchor}">'
            f'<span><strong>{_html_text(run_id)}</strong><small>{_html_text(run.get("completed_at") or run.get("started_at"))}</small></span>'
            f'<span>{_html_text(status)}</span>'
            f'<span class="badge {_score_class(run_score)}">{score_label}</span>'
            f"{current_badge}</a>"
        )
    if not rows:
        return '<div class="empty">暂无同计划历史报告</div>'
    return "\n".join(rows)


def _related_report_detail_sections_html(report: dict[str, Any], current_run_id: str) -> str:
    job_id = report.get("job_id")
    if not job_id:
        return ""
    sections: list[str] = []
    for run in list_runs(job_id=str(job_id), limit=20):
        run_id = str(run.get("id") or "")
        if not run_id or run_id == current_run_id:
            continue
        related = build_report(run_id)
        if not related:
            continue
        related_summary = related.get("summary") or {}
        related_score = related.get("score") or {}
        related_targets = related.get("targets") or []
        related_events = related.get("events") or []
        related_score_html = ""
        if related_score:
            related_score_html = (
                f'<div class="score compact {_score_class(related_score.get("score"))}">'
                f'{_html_text(related_score.get("score"))}<span>/100</span></div>'
            )
        related_metrics = "\n".join(
            [
                _html_metric("目标数", related_summary.get("target_count")),
                _html_metric("成功", related_summary.get("success_count"), "good"),
                _html_metric("失败", related_summary.get("error_count"), "bad" if related_summary.get("error_count") else ""),
                _html_metric("成功率", f"{related_summary.get('success_rate', 0)}%"),
            ]
        )
        related_events_html = "\n".join(
            f'<tr><td class="mono">{_html_text(event.get("time"))}</td>'
            f'<td>{_html_text(event.get("message") or event.get("type"))}</td>'
            f'<td>{_html_text(event.get("status"))}</td></tr>'
            for event in related_events[:20]
        )
        if not related_events_html:
            related_events_html = '<tr><td colspan="3" class="muted">暂无运行事件</td></tr>'
        related_targets_html = "\n".join(
            f"""
            <article class="target compact">
              <div class="target-head">
                <div><h3>{_html_text(target.get("host"))}</h3><p>#{_html_text(target.get("asset_id"))} · {_html_text(target.get("asset_type"))} / {_html_text(target.get("protocol"))}</p></div>
                <span class="badge {'good' if target.get('status') == 'success' else 'bad'}">{_html_text(target.get("status"))}</span>
              </div>
              {'<div class="error">' + _html_text(target.get("error")) + '</div>' if target.get("error") else ''}
              {'<pre>' + _html_text(str(target.get("result"))[:6000]) + '</pre>' if target.get("result") else ''}
            </article>
            """
            for target in related_targets
        )
        if not related_targets_html:
            related_targets_html = '<div class="empty">该报告暂无目标结果</div>'
        sections.append(
            f"""
            <section id="{_report_anchor(run_id)}" class="panel report-detail">
              <div class="section-head">
                <div>
                  <h2>历史报告 {_html_text(run_id)}</h2>
                  <p class="muted">{_html_text(related.get("message"))}</p>
                </div>
                {related_score_html}
              </div>
              <dl class="info-grid">
                <div><dt>计划编号</dt><dd>{_html_text(related.get("job_id"))}</dd></div>
                <div><dt>状态</dt><dd>{_html_text(related.get("status"))}</dd></div>
                <div><dt>范围</dt><dd>{_html_text(related.get("target_scope"))} / {_html_text(related.get("scope_value"))}</dd></div>
                <div><dt>完成</dt><dd>{_html_text(related.get("completed_at") or related.get("started_at"))}</dd></div>
              </dl>
              <div class="metric-grid related-metrics">{related_metrics}</div>
              <h3>运行事件</h3>
              <table><thead><tr><th>时间</th><th>事件</th><th>状态</th></tr></thead><tbody>{related_events_html}</tbody></table>
              <h3>目标结果</h3>
              {related_targets_html}
            </section>
            """
        )
    if not sections:
        return ""
    return "\n".join(sections)


def export_report_html(run_id: str) -> str | None:
    report = build_report(run_id)
    if not report:
        return None
    summary = report["summary"]
    score = report.get("score") or {}
    notification = report.get("notification") or {}
    events = report.get("events") or []
    trace = report.get("trace") or {}
    phases = trace.get("phases") or []
    targets = report.get("targets") or []
    title = f"巡检报告 {report.get('run_id') or ''}".strip()
    current_anchor = _report_anchor(str(report.get("run_id") or ""))

    nav_items = [
        ("report-index", "报告索引"),
        ("summary", "摘要"),
        ("score", "健康评分"),
        ("trace", "AIOps Run Trace"),
        ("notification", "通知"),
        ("events", "运行事件"),
        ("targets", "目标结果"),
    ]
    nav_html = "\n".join(
        f'<a href="#{anchor}">{label}</a>'
        for anchor, label in nav_items
        if anchor != "notification" or notification
    )
    summary_metrics = "\n".join(
        [
            _html_metric("目标数", summary["target_count"]),
            _html_metric("成功", summary["success_count"], "good"),
            _html_metric("失败", summary["error_count"], "bad" if summary["error_count"] else ""),
            _html_metric("成功率", f"{summary['success_rate']}%"),
        ]
    )
    report_index_html = _related_report_index_html(report, str(report.get("run_id") or ""))
    related_report_sections_html = _related_report_detail_sections_html(report, str(report.get("run_id") or ""))
    score_html = ""
    if score:
        dimensions_html = "\n".join(
            f'<div class="dimension {_score_class(dimension.get("score"))}">'
            f'<span>{_html_text(dimension.get("label") or dimension.get("id"))}</span>'
            f'<strong>{_html_text(dimension.get("score", 0))}</strong>'
            "</div>"
            for dimension in score.get("dimensions") or []
        )
        target_scores_html = "\n".join(
            f'<tr><td>{_html_text((item.get("target") or {}).get("host"))}</td>'
            f'<td>{_html_text(item.get("profile_label"))}</td>'
            f'<td><span class="badge {_score_class(item.get("score"))}">{_html_text(item.get("score"))}</span></td>'
            f'<td>{_html_text(item.get("grade_label"))}</td></tr>'
            for item in score.get("target_scores") or []
        )
        deductions_html = "\n".join(
            f'<li><strong>{_html_text(item.get("host"))}</strong> '
            f'<span class="badge bad">-{_html_text(item.get("points", 0))}</span> '
            f'{_html_text(item.get("reason"))}</li>'
            for item in score.get("deductions") or []
        )
        if not deductions_html:
            deductions_html = '<li class="muted">暂无明显扣分项</li>'
        score_html = f"""
        <section id="score" class="panel">
          <div class="section-head">
            <div>
              <h2>健康评分</h2>
              <p>{_html_text(score.get("profile_label"))} · {_html_text(score.get("grade_label"))}（{_html_text(score.get("grade"))}）</p>
            </div>
            <div class="score {_score_class(score.get("score"))}">{_html_text(score.get("score"))}<span>/100</span></div>
          </div>
          <div class="dimensions">{dimensions_html}</div>
          <div class="two-col">
            <div>
              <h3>目标得分</h3>
              <table>
                <thead><tr><th>目标</th><th>模型</th><th>分数</th><th>等级</th></tr></thead>
                <tbody>{target_scores_html}</tbody>
              </table>
            </div>
            <div>
              <h3>主要扣分</h3>
              <ul class="deductions">{deductions_html}</ul>
            </div>
          </div>
        </section>
        """
    trace_html = ""
    if phases:
        phase_html = "\n".join(
            f'<div class="phase"><span class="badge">{_html_text(phase.get("status"))}</span>'
            f'<strong>{_html_text(phase.get("label") or phase.get("id"))}</strong>'
            f'<p>{_html_text(phase.get("detail"))}</p>'
            f'<small>{_html_text(phase.get("completed_at") or phase.get("started_at"))}</small></div>'
            for phase in phases
        )
        trace_html = f"""
        <section id="trace" class="panel">
          <h2>AIOps Run Trace</h2>
          <p class="mono">{_html_text(trace.get("trace_id"))}</p>
          <div class="phase-grid">{phase_html}</div>
        </section>
        """
    notification_html = ""
    if notification:
        notification_html = f"""
        <section id="notification" class="panel">
          <h2>通知</h2>
          <dl class="info-grid">
            <div><dt>状态</dt><dd>{_html_text(notification.get("status"))}</dd></div>
            <div><dt>结果</dt><dd>{_html_text(notification.get("message"))}</dd></div>
          </dl>
        </section>
        """
    events_html = "\n".join(
        f'<tr><td class="mono">{_html_text(event.get("time"))}</td>'
        f'<td>{_html_text(event.get("message") or event.get("type"))}</td>'
        f'<td>{_html_text(event.get("status"))}</td></tr>'
        for event in events
    )
    if not events_html:
        events_html = '<tr><td colspan="3" class="muted">暂无运行事件</td></tr>'
    targets_html = "\n".join(
        f"""
        <article class="target">
          <div class="target-head">
            <div><h3>{_html_text(target.get("host"))}</h3><p>#{_html_text(target.get("asset_id"))} · {_html_text(target.get("asset_type"))} / {_html_text(target.get("protocol"))}</p></div>
            <span class="badge {'good' if target.get('status') == 'success' else 'bad'}">{_html_text(target.get("status"))}</span>
          </div>
          {'<div class="error">' + _html_text(target.get("error")) + '</div>' if target.get("error") else ''}
          {'<pre>' + _html_text(str(target.get("result"))[:12000]) + '</pre>' if target.get("result") else ''}
        </article>
        """
        for target in targets
    )
    if not targets_html:
        targets_html = '<div class="empty">报告中暂无目标结果</div>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html_text(title)}</title>
  <style>
    :root {{ color-scheme: light; --bg:#f4f7fb; --panel:#ffffff; --text:#172033; --sub:#64748b; --line:#d8e0ea; --good:#0f8a4b; --warn:#b7791f; --bad:#c2413a; --accent:#2563eb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; line-height:1.6; }}
    .shell {{ max-width:1180px; margin:0 auto; padding:28px 24px 56px; }}
    .hero {{ display:grid; gap:20px; grid-template-columns: 1.4fr .6fr; align-items:end; padding:28px; border:1px solid var(--line); background:linear-gradient(135deg,#fff,#eef5ff); border-radius:8px; }}
    .hero h1 {{ margin:0; font-size:30px; letter-spacing:0; }}
    .hero p,.muted {{ color:var(--sub); }}
    .nav {{ position:sticky; top:0; z-index:5; display:flex; flex-wrap:wrap; gap:10px; margin:18px 0; padding:12px; border:1px solid var(--line); border-radius:8px; background:rgba(255,255,255,.94); }}
    .nav a {{ color:var(--accent); text-decoration:none; font-weight:600; font-size:14px; }}
    .panel {{ margin-top:18px; padding:22px; border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:0 10px 30px rgba(15,23,42,.05); }}
    h2 {{ margin:0 0 14px; font-size:20px; }} h3 {{ margin:0 0 10px; font-size:15px; }}
    .metric-grid,.dimensions,.phase-grid {{ display:grid; gap:12px; }}
    .metric-grid {{ grid-template-columns: repeat(4,minmax(0,1fr)); }}
    .metric,.dimension,.phase {{ padding:14px; border:1px solid var(--line); border-radius:8px; background:#fbfdff; }}
    .metric-label,.dimension span,dt,small {{ color:var(--sub); font-size:12px; }}
    .metric-value {{ margin-top:4px; font-family:Consolas,monospace; font-size:24px; font-weight:800; }}
    .good {{ color:var(--good); }} .warn {{ color:var(--warn); }} .bad {{ color:var(--bad); }}
    .section-head,.target-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
    .score {{ font-family:Consolas,monospace; font-size:42px; font-weight:900; }} .score.compact {{ font-size:30px; }} .score span {{ font-size:15px; color:var(--sub); margin-left:4px; }}
    .dimensions {{ grid-template-columns: repeat(5,minmax(0,1fr)); margin:16px 0; }} .dimension strong {{ display:block; margin-top:4px; font:800 22px Consolas,monospace; }}
    .two-col {{ display:grid; grid-template-columns: 1fr 1fr; gap:16px; }}
    table {{ width:100%; border-collapse:collapse; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }} th {{ color:var(--sub); font-size:12px; }}
    .badge {{ display:inline-block; border-radius:999px; padding:2px 8px; background:#eef2f7; font-size:12px; font-weight:700; }}
    .badge.good {{ background:#e8f7ef; }} .badge.warn {{ background:#fff6db; }} .badge.bad {{ background:#fdecea; }}
    .info-grid {{ display:grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap:10px; margin:0; }} .info-grid div {{ padding:10px; border:1px solid var(--line); border-radius:8px; }} dd {{ margin:3px 0 0; font-weight:700; }}
    .phase-grid {{ grid-template-columns: repeat(4,minmax(0,1fr)); }} .phase p {{ min-height:48px; margin:8px 0; color:var(--sub); }}
    .deductions {{ margin:0; padding-left:18px; }} .deductions li {{ margin:8px 0; }}
    .target {{ margin-top:12px; padding:16px; border:1px solid var(--line); border-radius:8px; background:#fbfdff; }} .target.compact pre {{ max-height:320px; }} .target h3 {{ margin:0; }} .target p {{ margin:4px 0 0; color:var(--sub); }}
    .report-list {{ display:grid; gap:8px; }}
    .report-row {{ display:grid; grid-template-columns: minmax(0,1fr) 110px 80px 56px; align-items:center; gap:10px; padding:12px; border:1px solid var(--line); border-radius:8px; background:#fbfdff; color:var(--text); text-decoration:none; }}
    .report-row.current {{ border-color:var(--accent); background:#eef5ff; }}
    .report-row small {{ display:block; margin-top:2px; color:var(--sub); font-size:12px; }}
    .report-detail {{ scroll-margin-top: 84px; }} .related-metrics {{ margin:16px 0 18px; }}
    pre {{ max-height:520px; overflow:auto; white-space:pre-wrap; word-break:break-word; padding:14px; border:1px solid var(--line); border-radius:8px; background:#0f172a; color:#dbeafe; font-size:12px; }}
    .error {{ margin-top:12px; padding:10px; border:1px solid #f2b8b5; border-radius:8px; background:#fff1f0; color:var(--bad); }}
    .mono {{ font-family:Consolas,monospace; }} .empty {{ padding:24px; text-align:center; color:var(--sub); }}
    @media (max-width: 860px) {{ .hero,.two-col,.info-grid {{ grid-template-columns:1fr; }} .metric-grid,.dimensions,.phase-grid {{ grid-template-columns: repeat(2,minmax(0,1fr)); }} .report-row {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <header id="{current_anchor}" class="hero">
      <div>
        <p>OpsCore 自动巡检报告</p>
        <h1>{_html_text(title)}</h1>
        <p>{_html_text(report.get("message"))}</p>
      </div>
      <dl class="info-grid">
        <div><dt>运行编号</dt><dd>{_html_text(report.get("run_id"))}</dd></div>
        <div><dt>计划编号</dt><dd>{_html_text(report.get("job_id"))}</dd></div>
        <div><dt>状态</dt><dd>{_html_text(report.get("status"))}</dd></div>
        <div><dt>范围</dt><dd>{_html_text(report.get("target_scope"))} / {_html_text(report.get("scope_value"))}</dd></div>
        <div><dt>开始</dt><dd>{_html_text(report.get("started_at"))}</dd></div>
        <div><dt>完成</dt><dd>{_html_text(report.get("completed_at"))}</dd></div>
      </dl>
    </header>
    <nav class="nav">{nav_html}</nav>
    <section id="report-index" class="panel">
      <h2>报告索引</h2>
      <p class="muted">同一巡检计划最近 20 份报告，点击会跳转到本 HTML 内的报告详情；保存到本地后不依赖 OpsCore 服务。</p>
      <div class="report-list">{report_index_html}</div>
    </section>
    <section id="summary" class="panel">
      <h2>摘要</h2>
      <div class="metric-grid">{summary_metrics}</div>
    </section>
    {score_html}
    {trace_html}
    {notification_html}
    <section id="events" class="panel">
      <h2>运行事件</h2>
      <table><thead><tr><th>时间</th><th>事件</th><th>状态</th></tr></thead><tbody>{events_html}</tbody></table>
    </section>
    <section id="targets" class="panel">
      <h2>目标结果</h2>
      {targets_html}
    </section>
    {related_report_sections_html}
  </main>
</body>
</html>"""


def run_summary(limit: int = 5000) -> dict[str, Any]:
    with _LOCK:
        runs = _load()[: max(1, min(int(limit or 5000), 500))]
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
        _redact(run)
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
