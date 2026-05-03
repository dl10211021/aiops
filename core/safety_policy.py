import json
import os
import re
from typing import Any

from core.safety_action_classifiers import (
    _cmd_root,
    _sql_action_summary,
    _sql_actions,
    classify_linux_actions,
    classify_memcached_actions,
    classify_mongodb_actions,
    classify_network_actions,
    classify_redis_actions,
    classify_windows_actions,
)
from core.safety_action_decisions import (
    action_label as _resolve_action_label,
    action_reason as _resolve_action_reason,
    collect_action_rule_decisions,
    top_action_decision as _resolve_top_action_decision,
)
from core.safety_network_boundary import check_network_boundary as _evaluate_network_boundary
from core.safety_platform_actions import classify_platform_actions as _platform_actions
from core.safety_tool_categories import TOOL_CATEGORY
from core.safety_policy_config import (
    DEFAULT_SAFETY_POLICY,
    _deep_merge,
    _normalize_rules,
    _string_list,
    normalize_safety_policy,
    validate_safety_policy,
)
from core.safety_action_catalog import (
    ACTION_PRIORITY as _ACTION_PRIORITY,
    action_detail,
)


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
POLICY_PATH = os.path.join(ROOT_DIR, "safety_policy.json")

_SHELL_NOOP_REDIRECTION_RE = re.compile(
    r"(?:(?<=\s)|^)(?:[0-9]?>>?|&>)\s*/dev/null\b"
    r"|(?:(?<=\s)|^)[0-9]?>&[0-9]\b"
)


def get_safety_policy() -> dict[str, Any]:
    if not os.path.exists(POLICY_PATH):
        return normalize_safety_policy({})
    try:
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            return normalize_safety_policy(json.load(f))
    except Exception:
        return normalize_safety_policy({})


def save_safety_policy(policy: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_safety_policy(policy)
    issues = validate_safety_policy(normalized)
    if issues:
        raise ValueError("；".join(issues[:5]))
    tmp_path = f"{POLICY_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, POLICY_PATH)
    return normalized


def approval_timeout_seconds() -> int:
    return int(get_safety_policy().get("approval_timeout_seconds", 300))


def _category(tool_call_name: str, policy: dict[str, Any]) -> dict[str, Any]:
    name = TOOL_CATEGORY.get(tool_call_name, "")
    categories = policy.get("categories", {})
    return categories.get(name, {}) if isinstance(categories, dict) else {}


def _command_text(tool_call_name: str, args: dict[str, Any]) -> str:
    if tool_call_name == "db_execute_query":
        return str(args.get("sql") or "")
    if tool_call_name == "evolve_skill":
        return " ".join(
            str(args.get(key) or "")
            for key in ("skill_id", "file_name")
        )
    return str(args.get("command") or "")


def _http_policy_text(args: dict[str, Any]) -> str:
    body = args.get("body")
    body_text = ""
    if body is not None:
        try:
            body_text = json.dumps(body, ensure_ascii=False, sort_keys=True)
        except TypeError:
            body_text = str(body)
    return " ".join(
        str(args.get(key) or "")
        for key in ("method", "path", "url", "endpoint", "base_url", "operation", "oid")
    ) + (" " + body_text if body_text else "")


def _policy_match_text(tool_call_name: str, args: dict[str, Any]) -> str:
    command = _command_text(tool_call_name, args)
    if TOOL_CATEGORY.get(tool_call_name) in {"linux", "local"}:
        return _SHELL_NOOP_REDIRECTION_RE.sub(" ", command)
    if TOOL_CATEGORY.get(tool_call_name) == "http":
        return _http_policy_text(args)
    return command


def _regex_matches(patterns: list[str], text: str) -> bool:
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def _business_actions(tool_call_name: str, args: dict[str, Any]) -> list[dict[str, str]]:
    raw_actions = (
        _sql_actions(str(args.get("sql") or ""))
        if tool_call_name == "db_execute_query"
        else classify_linux_actions(str(args.get("command") or ""))
        if TOOL_CATEGORY.get(tool_call_name) == "linux"
        else classify_windows_actions(str(args.get("command") or ""))
        if TOOL_CATEGORY.get(tool_call_name) == "windows"
        else classify_redis_actions(str(args.get("command") or ""))
        if tool_call_name == "redis_execute_command"
        else classify_memcached_actions(str(args.get("command") or ""))
        if tool_call_name == "memcached_execute_command"
        else classify_mongodb_actions(str(args.get("command") or ""), operation=str(args.get("operation") or "find"))
        if tool_call_name == "mongodb_find"
        else classify_network_actions(str(args.get("command") or ""))
        if TOOL_CATEGORY.get(tool_call_name) == "network"
        else _platform_actions(tool_call_name, args)
    )
    raw_actions = sorted(raw_actions, key=lambda action: _ACTION_PRIORITY.get(action, 100))
    actions: list[dict[str, str]] = []
    seen: set[str] = set()
    for action in raw_actions:
        if action in seen:
            continue
        seen.add(action)
        detail = action_detail(action)
        if detail:
            actions.append({"id": action, **detail})
            continue
        actions.append(
            {
                "id": action,
                "label": action,
                "description": "命中平台动作规则。",
                "severity": "medium",
            }
        )
    return actions


def _semantic_text(tool_call_name: str, args: dict[str, Any]) -> str:
    parts = [
        _command_text(tool_call_name, args),
        str(args.get("method") or ""),
        str(args.get("path") or ""),
        str(args.get("oid") or ""),
        " ".join(_platform_actions(tool_call_name, args)),
        " ".join(_sql_actions(str(args.get("sql") or ""))) if tool_call_name == "db_execute_query" else "",
        " ".join(classify_linux_actions(str(args.get("command") or ""))) if TOOL_CATEGORY.get(tool_call_name) == "linux" else "",
        " ".join(classify_windows_actions(str(args.get("command") or ""))) if TOOL_CATEGORY.get(tool_call_name) == "windows" else "",
        " ".join(classify_redis_actions(str(args.get("command") or ""))) if tool_call_name == "redis_execute_command" else "",
        " ".join(classify_memcached_actions(str(args.get("command") or ""))) if tool_call_name == "memcached_execute_command" else "",
        " ".join(classify_mongodb_actions(str(args.get("command") or ""), operation=str(args.get("operation") or "find"))) if tool_call_name == "mongodb_find" else "",
        " ".join(classify_network_actions(str(args.get("command") or ""))) if TOOL_CATEGORY.get(tool_call_name) == "network" else "",
    ]
    return " ".join(part for part in parts if part).strip()


def _semantic_matcher_matches(matcher: dict[str, Any], text: str, args: dict[str, Any]) -> bool:
    matcher_type = str(matcher.get("type") or "").lower()
    value = str(matcher.get("value") or "").strip()
    if not value:
        return False

    lower_text = text.lower()
    lower_value = value.lower()
    if matcher_type in {"contains", "substring"}:
        return lower_value in lower_text
    if matcher_type in {"prefix", "command_prefix"}:
        return lower_text.strip().startswith(lower_value)
    if matcher_type in {"equals", "exact"}:
        return lower_text.strip() == lower_value
    if matcher_type in {"http_method", "method"}:
        return str(args.get("method") or "").upper() == value.upper()
    if matcher_type in {"api_path_contains", "path_contains"}:
        return lower_value in str(args.get("path") or "").lower()
    if matcher_type in {"api_path_prefix", "path_prefix"}:
        return str(args.get("path") or "").lower().startswith(lower_value)
    if matcher_type == "platform_action":
        return lower_value in lower_text
    if matcher_type == "sql_action":
        return lower_value in _sql_actions(str(args.get("sql") or "")) or lower_value in lower_text
    if matcher_type == "linux_action":
        return lower_value in classify_linux_actions(str(args.get("command") or "")) or lower_value in lower_text
    if matcher_type == "windows_action":
        return lower_value in classify_windows_actions(str(args.get("command") or "")) or lower_value in lower_text
    if matcher_type == "redis_action":
        return lower_value in classify_redis_actions(str(args.get("command") or "")) or lower_value in lower_text
    if matcher_type == "memcached_action":
        return lower_value in classify_memcached_actions(str(args.get("command") or "")) or lower_value in lower_text
    if matcher_type == "mongodb_action":
        return lower_value in classify_mongodb_actions(str(args.get("command") or ""), operation=str(args.get("operation") or "find")) or lower_value in lower_text
    if matcher_type == "network_action":
        return lower_value in classify_network_actions(str(args.get("command") or "")) or lower_value in lower_text
    if matcher_type == "regex":
        try:
            return bool(re.search(value, text, re.IGNORECASE))
        except re.error:
            return False
    return False


def _rule_applies(rule: dict[str, Any], tool_call_name: str, context: dict[str, Any]) -> bool:
    if not rule.get("enabled", True):
        return False

    sources = _string_list(rule.get("sources", []))
    trigger_source = str(context.get("trigger_source") or context.get("source") or "chat").strip().lower()
    if sources and trigger_source not in {item.lower() for item in sources}:
        return False

    rule_category = str(rule.get("category") or "").strip()
    tool_category = TOOL_CATEGORY.get(tool_call_name, "")
    if rule_category and rule_category not in {tool_category, "http_api"}:
        return False

    platform = str(rule.get("platform") or "").strip().lower()
    asset_type = str(context.get("asset_type") or "").strip().lower()
    protocol = str(context.get("protocol") or "").strip().lower()
    platform_aliases = {
        "linux": {"linux", "ssh", "kvm"},
        "windows": {"windows", "winrm"},
        "kvm host": {"linux", "ssh", "kvm"},
        "s3": {"s3", "minio", "ceph rgw", "oss", "cos", "obs", "http_api"},
        "kubernetes": {"k8s", "kubernetes"},
        "nvidia gpu": {"gpu", "nvidia", "ai", "ai_platform"},
        "ci/cd": {"cicd", "jenkins", "gitlab", "argocd"},
    }
    aliases = platform_aliases.get(platform, {platform})
    observed = {asset_type, protocol}
    if platform and any(observed):
        direct_match = any(alias and any(alias in item or item in alias for item in observed if item) for alias in aliases)
        if not direct_match:
            return False

    scope = rule.get("scope") if isinstance(rule.get("scope"), dict) else {}
    scope_type = str(scope.get("type") or "all").strip().lower()
    scope_value = str(scope.get("value") or "").strip().lower()
    if scope_type and scope_type != "all" and scope_value:
        tags = [str(item).lower() for item in context.get("tags", []) if str(item).strip()]
        context_values = {
            "asset_type": asset_type,
            "protocol": protocol,
            "platform": str(context.get("platform") or context.get("platform_name") or "").lower(),
            "asset_group": str(context.get("target_scope") or context.get("scope_value") or context.get("group_name") or "").lower(),
            "tag": " ".join(tags),
            "environment": str(context.get("environment") or "").lower(),
            "data_center": str(context.get("data_center") or context.get("datacenter") or context.get("az") or "").lower(),
            "tenant": str(context.get("tenant") or context.get("business") or context.get("business_unit") or "").lower(),
            "asset": str(context.get("host") or context.get("asset_id") or "").lower(),
        }
        if scope_type == "tag":
            if scope_value not in tags:
                return False
        elif scope_value not in context_values.get(scope_type, ""):
            return False

    return True


def _matched_semantic_rule(
    policy: dict[str, Any],
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    decisions: set[str],
) -> dict[str, Any] | None:
    text = _semantic_text(tool_call_name, args)
    for rule in policy.get("rules", []):
        if rule.get("decision") not in decisions:
            continue
        if not _rule_applies(rule, tool_call_name, context):
            continue
        if any(_semantic_matcher_matches(matcher, text, args) for matcher in rule.get("matchers", [])):
            return rule
    return None


def _rule_reason(rule: dict[str, Any], fallback: str) -> str:
    name = str(rule.get("name") or "安全策略规则")
    description = str(rule.get("description") or "").strip()
    if description:
        return f"{name}: {description}"
    return f"{name}: {fallback}"


def _tool_actions(tool_call_name: str, args: dict[str, Any]) -> list[str]:
    if TOOL_CATEGORY.get(tool_call_name) == "linux":
        return classify_linux_actions(str(args.get("command") or ""))
    if TOOL_CATEGORY.get(tool_call_name) == "windows":
        return classify_windows_actions(str(args.get("command") or ""))
    if tool_call_name == "redis_execute_command":
        return classify_redis_actions(str(args.get("command") or ""))
    if tool_call_name == "memcached_execute_command":
        return classify_memcached_actions(str(args.get("command") or ""))
    if tool_call_name == "mongodb_find":
        return classify_mongodb_actions(str(args.get("command") or ""), operation=str(args.get("operation") or "find"))
    if TOOL_CATEGORY.get(tool_call_name) == "network":
        return classify_network_actions(str(args.get("command") or ""))
    if tool_call_name == "db_execute_query":
        return _sql_actions(str(args.get("sql") or ""))
    return _platform_actions(tool_call_name, args)


def _action_rule_decisions(policy: dict[str, Any], tool_call_name: str, args: dict[str, Any]) -> list[tuple[str, str]]:
    return collect_action_rule_decisions(
        policy,
        category=TOOL_CATEGORY.get(tool_call_name, ""),
        actions=_tool_actions(tool_call_name, args),
    )


def _action_label(action: str) -> str:
    return _resolve_action_label(action)


def _action_reason(action: str, decision: str) -> str:
    return _resolve_action_reason(action, decision)


def _top_action_decision(policy: dict[str, Any], tool_call_name: str, args: dict[str, Any]) -> tuple[str, str, str]:
    return _resolve_top_action_decision(
        policy,
        category=TOOL_CATEGORY.get(tool_call_name, ""),
        actions=_tool_actions(tool_call_name, args),
    )


def check_network_boundary(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    return _evaluate_network_boundary(
        tool_call_name,
        args,
        context,
        policy=get_safety_policy(),
        tool_category=TOOL_CATEGORY,
    )


def check_approval_needed(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    policy = get_safety_policy()
    cfg = _category(tool_call_name, policy)
    if not cfg:
        return False, ""

    if tool_call_name in {"redis_execute_command", "memcached_execute_command"}:
        root = _cmd_root(_command_text(tool_call_name, args))
        if root in cfg.get("approval_commands", []):
            label = "Memcached" if tool_call_name == "memcached_execute_command" else "Redis"
            return True, f"检测到 {label} 写操作或高危命令。"

    _, action_decision, action_reason = _top_action_decision(policy, tool_call_name, args)
    if action_decision == "approval":
        semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
        if semantic_rule:
            return True, _rule_reason(semantic_rule, "该动作需要人工审批。")
        return True, action_reason
    if action_decision in {"allow", "deny"}:
        return False, ""

    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "该动作需要人工审批。")

    if cfg.get("always_approval"):
        return True, cfg.get("approval_reason") or "该工具调用需要人工审批。"

    if TOOL_CATEGORY.get(tool_call_name) == "http":
        method = str(args.get("method") or "GET").upper()
        if method in cfg.get("approval_methods", []):
            return True, f"HTTP {method} 可能改变目标系统状态，需要确认。"
        return False, ""

    command = _policy_match_text(tool_call_name, args)
    if _regex_matches(cfg.get("approval_patterns", []), command):
        if TOOL_CATEGORY.get(tool_call_name, "") == "sql":
            return True, _sql_action_summary(command)[1]
        reason = {
            "linux": "检测到可能改变 Linux/KVM 系统状态的命令。",
            "windows": "检测到可能改变 Windows 系统状态的命令。",
            "sql": "检测到数据库数据修改或结构变更操作。",
            "network": "检测到可能改变网络设备配置或状态的命令。",
        }.get(TOOL_CATEGORY.get(tool_call_name, ""), "检测到高危操作。")
        return True, reason

    if tool_call_name in {"linux_execute_command", "execute_on_scope"} and not context.get("allow_modifications", False):
        root = _cmd_root(command)
        safe_roots = cfg.get("readonly_safe_roots", [])
        if cfg.get("readonly_unknown_requires_approval", False) and root and root not in safe_roots:
            return True, f"只读模式下的未知命令需要确认: {root}"

    return False, ""


def check_readonly_block(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    if context.get("allow_modifications", False):
        return False, ""

    policy = get_safety_policy()
    cfg = _category(tool_call_name, policy)
    if not cfg:
        return False, ""

    if tool_call_name in {"redis_execute_command", "memcached_execute_command"}:
        root = _cmd_root(_command_text(tool_call_name, args))
        if root in cfg.get("readonly_block_commands", []):
            label = "Memcached" if tool_call_name == "memcached_execute_command" else "Redis"
            return True, f"只读安全模式，已拦截潜在的 {label} 修改动作"

    _, action_decision, action_reason = _top_action_decision(policy, tool_call_name, args)
    if action_decision in {"approval", "deny"}:
        if action_decision == "approval":
            semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
            if semantic_rule:
                return True, _rule_reason(semantic_rule, "只读会话不执行需要审批的变更动作。")
        return True, f"只读安全模式，已拦截：{action_reason}"
    if action_decision == "allow":
        return False, ""

    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "只读会话不执行需要审批的变更动作。")

    if TOOL_CATEGORY.get(tool_call_name) == "http":
        method = str(args.get("method") or "GET").upper()
        if method in cfg.get("readonly_block_methods", []):
            return True, f"只读安全模式，已拦截 HTTP {method} 请求"
        return False, ""

    command = _policy_match_text(tool_call_name, args)
    if _regex_matches(cfg.get("readonly_block_patterns", []), command):
        if TOOL_CATEGORY.get(tool_call_name, "") == "sql":
            return True, f"只读安全模式，已拦截潜在的{_sql_action_summary(command)[0]}动作"
        label = {
            "local": "本地脚本",
            "linux": "Linux/KVM",
            "windows": "Windows",
            "sql": "数据库",
            "network": "网络设备",
        }.get(TOOL_CATEGORY.get(tool_call_name, ""), "目标系统")
        return True, f"只读安全模式，已拦截潜在的 {label} 修改动作"

    return False, ""


def check_hard_block(tool_call_name: str, args: dict[str, Any], context: dict[str, Any] | None = None) -> tuple[bool, str]:
    policy = get_safety_policy()
    network_blocked, network_reason = check_network_boundary(tool_call_name, args, context or {})
    if network_blocked:
        return True, network_reason

    _, action_decision, action_reason = _top_action_decision(policy, tool_call_name, args)
    if action_decision == "allow":
        return False, ""

    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context or {}, {"deny"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "该动作被配置为禁止执行。")

    cfg = _category(tool_call_name, policy)
    command = _policy_match_text(tool_call_name, args).lower()
    for marker in cfg.get("hard_block_substrings", []):
        if marker and marker in command:
            if TOOL_CATEGORY.get(tool_call_name, "") == "sql":
                return True, f"{_sql_action_summary(command)[0]}触发硬拦截策略，已被系统拒绝。"
            return True, "指令触发硬拦截策略，已被系统拒绝。"

    if action_decision == "deny":
        return True, action_reason
    return False, ""


def explain_policy_decision(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preview how a tool call would be handled without executing it."""
    ctx = context or {}
    mode = "readwrite" if ctx.get("allow_modifications", False) else "readonly"
    checks: list[dict[str, Any]] = []
    policy = get_safety_policy()
    actions = _business_actions(tool_call_name, args)
    action_id, action_decision, action_reason = _top_action_decision(policy, tool_call_name, args)
    network_blocked, network_reason = check_network_boundary(tool_call_name, args, ctx)

    def layer_payload(
        layer_id: str,
        label: str,
        matched: bool,
        reason: str = "",
        priority: int = 0,
    ) -> dict[str, Any]:
        return {
            "id": layer_id,
            "label": label,
            "matched": matched,
            "reason": reason,
            "priority": priority,
        }

    def build_layers(
        final_decision: str,
        final_reason: str,
        resolution_layer: str,
    ) -> list[dict[str, Any]]:
        action_matched = bool(action_decision)
        return [
            layer_payload(
                "network_boundary",
                "网络边界",
                network_blocked,
                network_reason,
                1,
            ),
            layer_payload(
                "advanced_deny",
                "高级禁止兜底",
                resolution_layer == "advanced_deny",
                final_reason if resolution_layer == "advanced_deny" else "",
                2,
            ),
            layer_payload(
                "action_policy",
                "动作权限",
                action_matched,
                action_reason,
                3,
            ),
            layer_payload(
                "advanced_fallback",
                "高级审批/只读兜底",
                resolution_layer == "advanced_fallback",
                final_reason if resolution_layer == "advanced_fallback" else "",
                4,
            ),
            layer_payload(
                "default",
                "默认放行",
                final_decision == "allow" and not action_matched,
                "未命中网络边界、高级兜底或动作权限，按默认只读查询放行。"
                if final_decision == "allow" and not action_matched
                else "",
                5,
            ),
        ]

    def result_payload(decision: str, label: str, reason: str, resolution_layer: str) -> dict[str, Any]:
        return {
            "decision": decision,
            "label": label,
            "mode": mode,
            "reason": reason,
            "checks": checks,
            "actions": actions,
            "primary_action": actions[0] if actions else None,
            "resolution_layer": resolution_layer,
            "policy_layers": build_layers(decision, reason, resolution_layer),
        }

    hard_blocked, hard_reason = check_hard_block(tool_call_name, args, ctx)
    checks.append(
        {
            "name": "禁止执行",
            "matched": hard_blocked,
            "reason": hard_reason,
        }
    )
    if hard_blocked:
        if network_blocked:
            layer = "network_boundary"
        elif action_decision == "deny" and hard_reason == action_reason:
            layer = "action_policy"
        else:
            layer = "advanced_deny"
        return result_payload("deny", "禁止执行", hard_reason, layer)

    needs_approval, approval_reason = check_approval_needed(tool_call_name, args, ctx)
    readonly_blocked, readonly_reason = check_readonly_block(tool_call_name, args, ctx)
    checks.extend(
        [
            {
                "name": "需要审批",
                "matched": needs_approval,
                "reason": approval_reason,
            },
            {
                "name": "只读保护",
                "matched": readonly_blocked,
                "reason": readonly_reason,
            },
        ]
    )

    if readonly_blocked:
        layer = "action_policy" if action_decision in {"approval", "deny"} else "advanced_fallback"
        return result_payload("readonly_block", "只读保护阻止", readonly_reason, layer)

    if needs_approval:
        layer = "action_policy" if action_decision == "approval" else "advanced_fallback"
        return result_payload("approval", "需要审批", approval_reason, layer)

    layer = "action_policy" if action_decision == "allow" else "default"
    return result_payload("allow", "允许执行", "未命中审批或禁止执行规则。", layer)
