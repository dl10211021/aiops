"""Alert classification, noise reduction, and automation policy helpers."""

from __future__ import annotations

from typing import Any


RECOVERY_STATUSES = {"resolved", "ok", "closed", "recovered", "recovery"}

SEVERITY_PRIORITY: dict[str, str] = {
    "disaster": "p0",
    "critical": "p0",
    "fatal": "p0",
    "high": "p1",
    "error": "p1",
    "major": "p1",
    "warning": "p2",
    "warn": "p2",
    "average": "p2",
    "minor": "p3",
    "info": "p4",
    "information": "p4",
    "ok": "p4",
    "resolved": "p4",
}

SOURCE_FAMILY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("zabbix", ("zabbix", "triggerid", "eventid", "host.host", "itemid")),
    ("prometheus", ("prometheus", "alertmanager", "promql", "prometheusreplica")),
    ("grafana", ("grafana", "ruleurl", "dashboardurl", "panelurl")),
    ("manageengine", ("manageengine", "opmanager", "site24x7", "monitorname")),
)

ALERT_CLASS_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("network", ("interface", "port", "bgp", "ospf", "isis", "link down", "链路", "端口", "交换机")),
    ("database", ("mysql", "oracle", "postgres", "postgresql", "mongodb", "tidb", "redis", "database", "db ")),
    ("capacity", ("disk", "filesystem", "inode", "space", "volume", "capacity", "磁盘", "空间")),
    ("performance", ("cpu", "memory", "load", "latency", "slow", "timeout", "响应", "延迟", "负载")),
    ("availability", ("down", "unreachable", "unavailable", "failed", "not responding", "宕机", "不可达")),
    ("security", ("login", "auth", "password", "failed password", "acl", "security", "认证", "登录")),
)


def _text_blob(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            parts.extend(f"{key}={item}" for key, item in value.items())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts).lower()


def classify_alert_source(alert: dict[str, Any]) -> str:
    source_type = str(alert.get("source_type") or "").lower()
    source = str(alert.get("source") or "").lower()
    payload = alert.get("payload") if isinstance(alert.get("payload"), dict) else {}
    labels = alert.get("labels") if isinstance(alert.get("labels"), dict) else {}
    text = _text_blob(source_type, source, payload, labels)
    for family, aliases in SOURCE_FAMILY_ALIASES:
        if source_type == family or any(alias in text for alias in aliases):
            if family == "prometheus" and source_type == "grafana":
                continue
            return family
    if source_type in {"webhook", ""}:
        return "generic"
    return source_type


def classify_alert_class(alert: dict[str, Any]) -> str:
    text = _text_blob(
        alert.get("alert_name"),
        alert.get("description"),
        alert.get("labels") if isinstance(alert.get("labels"), dict) else {},
        alert.get("annotations") if isinstance(alert.get("annotations"), dict) else {},
    )
    for alert_class, keywords in ALERT_CLASS_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return alert_class
    return "unknown"


def priority_for_severity(severity: Any) -> str:
    value = str(severity or "warning").lower()
    return SEVERITY_PRIORITY.get(value, "p2")


def _is_recovery(alert: dict[str, Any]) -> bool:
    status_hint = str(alert.get("status_hint") or "").lower()
    severity = str(alert.get("severity") or "").lower()
    return bool(alert.get("ends_at")) or status_hint in RECOVERY_STATUSES or severity in RECOVERY_STATUSES


def build_alert_policy(alert: dict[str, Any]) -> dict[str, Any]:
    source_family = classify_alert_source(alert)
    alert_class = classify_alert_class(alert)
    priority = priority_for_severity(alert.get("severity"))
    repeat_count = int(alert.get("repeat_count") or 1)
    is_recovery = _is_recovery(alert) or str(alert.get("status") or "").lower() == "closed"

    if is_recovery:
        noise_action = "close"
        run_ai = False
        notify = False
        reason = "恢复类告警只更新事件状态，不自动拉起 AI。"
    elif priority in {"p0", "p1"}:
        noise_action = "analyze"
        run_ai = True
        notify = True
        reason = "高优先级故障需要自动启动 AI 排查并通知值班人。"
    elif priority == "p2" and alert_class in {"availability", "capacity", "performance", "network", "database"}:
        noise_action = "analyze"
        run_ai = True
        notify = True
        reason = "中优先级基础设施告警进入自动分析队列。"
    elif repeat_count >= 3 and priority in {"p2", "p3"}:
        noise_action = "dedupe_escalate"
        run_ai = True
        notify = priority == "p2"
        reason = "重复告警达到阈值，按降噪升级策略进入分析。"
    else:
        noise_action = "record_only"
        run_ai = False
        notify = False
        reason = "低优先级或信息类告警只记录，不自动启动 AI。"

    return {
        "source_family": source_family,
        "alert_class": alert_class,
        "priority": priority,
        "noise_action": noise_action,
        "automation_decision": {
            "run_ai": run_ai,
            "notify": notify,
            "reason": reason,
        },
        "notification_plan": {
            "channel": "auto" if notify else "none",
            "when": "analysis_complete" if notify and run_ai else "none",
            "targets": ["wechat", "dingtalk", "email"] if notify else [],
        },
    }
