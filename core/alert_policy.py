"""Alert classification, noise reduction, and automation policy helpers."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any


RECOVERY_STATUSES = {"resolved", "ok", "closed", "recovered", "recovery"}
ZERO_TIME_PREFIXES = ("0001-01-01", "1970-01-01")
ROOT_DIR = Path(__file__).resolve().parent.parent
ALERT_POLICY_CONFIG_PATH = ROOT_DIR / "alert_policy_config.json"
_POLICY_LOCK = threading.RLock()

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

DEFAULT_ALERT_AUTOMATION_POLICY: dict[str, Any] = {
    "version": 1,
    "rules": [
        {
            "id": "recovery-record",
            "name": "恢复类告警仅闭环",
            "enabled": True,
            "conditions": {"recovery": True},
            "action": "close",
            "notify": False,
            "channels": [],
            "remediation_mode": "disabled",
            "allowed_remediation_actions": [],
            "cooldown_minutes": 30,
            "reason": "恢复类告警只更新事件状态，不自动拉起 AI。",
        },
        {
            "id": "default-record-only",
            "name": "默认仅记录",
            "enabled": True,
            "conditions": {},
            "action": "record_only",
            "notify": False,
            "channels": [],
            "remediation_mode": "disabled",
            "allowed_remediation_actions": [],
            "cooldown_minutes": 30,
            "reason": "低优先级或信息类告警只记录，不自动启动 AI。",
        },
    ],
}


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


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [item.strip() for item in re.split(r"[,，\n]", value)]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value]
    else:
        raw_items = [str(value).strip()]
    return [item.lower() for item in raw_items if item]


def _bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled", "启用", "是"}


def _cooldown_minutes(value: Any, default: int = 30) -> int:
    try:
        return max(1, min(int(value), 1440))
    except (TypeError, ValueError):
        return default


def normalize_alert_automation_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    source = policy if isinstance(policy, dict) else {}
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(source.get("rules") if isinstance(source.get("rules"), list) else []):
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("id") or f"rule-{index + 1}").strip() or f"rule-{index + 1}"
        conditions = item.get("conditions") if isinstance(item.get("conditions"), dict) else {}
        action = str(item.get("action") or "record_only").strip().lower()
        if action not in {"record_only", "analyze", "dedupe_escalate", "suppress", "close"}:
            action = "record_only"
        normalized_conditions = {
            "source_families": _string_list(conditions.get("source_families")),
            "severities": _string_list(conditions.get("severities")),
            "alert_classes": _string_list(conditions.get("alert_classes")),
            "priorities": _string_list(conditions.get("priorities")),
            "host_contains": _string_list(conditions.get("host_contains")),
            "name_contains": _string_list(conditions.get("name_contains")),
            "label_contains": _string_list(conditions.get("label_contains")),
        }
        if conditions.get("min_repeat_count") not in (None, ""):
            try:
                normalized_conditions["min_repeat_count"] = max(1, int(conditions.get("min_repeat_count")))
            except (TypeError, ValueError):
                normalized_conditions["min_repeat_count"] = 1
        if conditions.get("recovery") is not None:
            normalized_conditions["recovery"] = _bool_value(conditions.get("recovery"))
        notify = _bool_value(item.get("notify"), action in {"analyze", "dedupe_escalate"})
        channels = _string_list(item.get("channels"))
        if notify and not channels:
            channels = ["wechat", "dingtalk", "email"]
        remediation_mode = str(item.get("remediation_mode") or "disabled").strip().lower()
        if remediation_mode not in {"disabled", "suggest", "approval", "auto_low_risk"}:
            remediation_mode = "disabled"
        rules.append(
            {
                "id": rule_id,
                "name": str(item.get("name") or rule_id).strip() or rule_id,
                "enabled": _bool_value(item.get("enabled"), True),
                "conditions": normalized_conditions,
                "action": action,
                "notify": notify,
                "channels": channels,
                "remediation_mode": remediation_mode,
                "allowed_remediation_actions": _string_list(item.get("allowed_remediation_actions")),
                "cooldown_minutes": _cooldown_minutes(item.get("cooldown_minutes")),
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    if not rules:
        return json.loads(json.dumps(DEFAULT_ALERT_AUTOMATION_POLICY, ensure_ascii=False))
    return {"version": int(source.get("version") or 1), "rules": rules}


def get_alert_automation_policy() -> dict[str, Any]:
    with _POLICY_LOCK:
        if not ALERT_POLICY_CONFIG_PATH.exists():
            return normalize_alert_automation_policy(DEFAULT_ALERT_AUTOMATION_POLICY)
        try:
            data = json.loads(ALERT_POLICY_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return normalize_alert_automation_policy(DEFAULT_ALERT_AUTOMATION_POLICY)
        return normalize_alert_automation_policy(data if isinstance(data, dict) else {})


def save_alert_automation_policy(policy: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_alert_automation_policy(policy)
    with _POLICY_LOCK:
        ALERT_POLICY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ALERT_POLICY_CONFIG_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


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
    ends_at = str(alert.get("ends_at") or "").strip().lower()
    has_real_end = bool(ends_at) and not any(ends_at.startswith(prefix) for prefix in ZERO_TIME_PREFIXES)
    return has_real_end or status_hint in RECOVERY_STATUSES or severity in RECOVERY_STATUSES


def _rule_matches(rule: dict[str, Any], alert: dict[str, Any], policy_context: dict[str, Any]) -> bool:
    if not rule.get("enabled", True):
        return False
    conditions = rule.get("conditions") if isinstance(rule.get("conditions"), dict) else {}
    source_family = str(policy_context.get("source_family") or "").lower()
    alert_class = str(policy_context.get("alert_class") or "").lower()
    priority = str(policy_context.get("priority") or "").lower()
    severity = str(alert.get("severity") or "").lower()
    host = str(alert.get("host") or "").lower()
    alert_name = str(alert.get("alert_name") or "").lower()
    labels = alert.get("labels") if isinstance(alert.get("labels"), dict) else {}
    annotations = alert.get("annotations") if isinstance(alert.get("annotations"), dict) else {}
    label_text = _text_blob(labels, annotations)

    condition_checks = (
        ("source_families", source_family),
        ("severities", severity),
        ("alert_classes", alert_class),
        ("priorities", priority),
    )
    for key, actual in condition_checks:
        expected = _string_list(conditions.get(key))
        if expected and actual not in expected:
            return False

    host_contains = _string_list(conditions.get("host_contains"))
    if host_contains and not any(item in host for item in host_contains):
        return False
    name_contains = _string_list(conditions.get("name_contains"))
    if name_contains and not any(item in alert_name for item in name_contains):
        return False
    label_contains = _string_list(conditions.get("label_contains"))
    if label_contains and not any(item in label_text for item in label_contains):
        return False
    if conditions.get("min_repeat_count") not in (None, ""):
        try:
            if int(policy_context.get("repeat_count") or 1) < int(conditions.get("min_repeat_count")):
                return False
        except (TypeError, ValueError):
            return False
    if conditions.get("recovery") is not None and bool(policy_context.get("is_recovery")) != _bool_value(conditions.get("recovery")):
        return False
    return True


def _policy_result_for_rule(rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    action = str(rule.get("action") or "record_only").lower()
    notify = _bool_value(rule.get("notify"), action in {"analyze", "dedupe_escalate"})
    if action in {"record_only", "suppress", "close"}:
        run_ai = False
        notify = False
    else:
        run_ai = True
    channels = _string_list(rule.get("channels")) if notify else []
    reason = str(rule.get("reason") or "").strip()
    if not reason:
        reason = f"命中告警策略：{rule.get('name') or rule.get('id') or '-'}。"
    return {
        "source_family": context["source_family"],
        "alert_class": context["alert_class"],
        "priority": context["priority"],
        "noise_action": action,
        "automation_decision": {
            "run_ai": run_ai,
            "notify": notify,
            "reason": reason,
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "remediation_mode": rule.get("remediation_mode") or "disabled",
            "allowed_remediation_actions": _string_list(rule.get("allowed_remediation_actions")),
            "cooldown_minutes": _cooldown_minutes(rule.get("cooldown_minutes")),
        },
        "notification_plan": {
            "channel": "auto" if notify else "none",
            "when": "analysis_complete" if notify and run_ai else "none",
            "targets": channels,
        },
    }


def build_alert_policy(alert: dict[str, Any]) -> dict[str, Any]:
    source_family = classify_alert_source(alert)
    alert_class = classify_alert_class(alert)
    priority = priority_for_severity(alert.get("severity"))
    repeat_count = int(alert.get("repeat_count") or 1)
    is_recovery = _is_recovery(alert) or str(alert.get("status") or "").lower() == "closed"
    context = {
        "source_family": source_family,
        "alert_class": alert_class,
        "priority": priority,
        "repeat_count": repeat_count,
        "is_recovery": is_recovery,
    }
    for rule in get_alert_automation_policy().get("rules", []):
        if _rule_matches(rule, alert, context):
            return _policy_result_for_rule(rule, context)
    return _policy_result_for_rule(DEFAULT_ALERT_AUTOMATION_POLICY["rules"][-1], context)


def explain_alert_policy_for_payload(payload: dict[str, Any]) -> dict[str, Any]:
    alert = dict(payload or {})
    if "source_family" not in alert:
        alert["source_family"] = classify_alert_source(alert)
    if "alert_class" not in alert:
        alert["alert_class"] = classify_alert_class(alert)
    alert.setdefault("repeat_count", 1)
    decision = build_alert_policy(alert)
    return {"alert": alert, "policy": decision}
