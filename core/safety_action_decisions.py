from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.safety_action_catalog import ACTION_PRIORITY, action_detail


def collect_action_rule_decisions(
    policy: dict[str, Any],
    *,
    category: str,
    actions: Iterable[str],
) -> list[tuple[str, str]]:
    if not category:
        return []
    rules = policy.get("action_rules", {}).get(category, {})
    if not isinstance(rules, dict):
        return []

    decisions: list[tuple[str, str]] = []
    for action in sorted(actions, key=lambda item: ACTION_PRIORITY.get(item, 100)):
        decision = str(rules.get(action) or "").strip().lower()
        if decision in {"allow", "approval", "deny"}:
            decisions.append((action, decision))
    return decisions


def action_label(action: str) -> str:
    detail = action_detail(action)
    if detail:
        return str(detail.get("label") or action)
    return action


def action_reason(action: str, decision: str) -> str:
    label = action_label(action)
    if action == "sql.instance_admin":
        label = "数据库实例级管理"
    if decision == "deny":
        return f"{label} 已被动作策略设置为禁止执行。"
    if decision == "approval":
        return f"{label} 已被动作策略设置为需要人工审批。"
    return f"{label} 已被动作策略设置为允许。"


def top_action_decision(
    policy: dict[str, Any],
    *,
    category: str,
    actions: Iterable[str],
) -> tuple[str, str, str]:
    decisions = collect_action_rule_decisions(policy, category=category, actions=actions)
    for action, decision in decisions:
        if decision == "deny":
            return action, decision, action_reason(action, decision)
    for action, decision in decisions:
        if decision == "approval":
            return action, decision, action_reason(action, decision)
    if decisions and all(decision == "allow" for _, decision in decisions):
        action = decisions[0][0]
        return action, "allow", action_reason(action, "allow")
    return "", "", ""
