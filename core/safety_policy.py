import json
import os
import re
from copy import deepcopy
from typing import Any


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
POLICY_PATH = os.path.join(ROOT_DIR, "safety_policy.json")


DEFAULT_SAFETY_POLICY: dict[str, Any] = {
    "version": 1,
    "approval_timeout_seconds": 300,
    "readwrite_chat_warning_enabled": True,
    "rules": [],
    "categories": {
        "local": {
            "always_approval": True,
            "approval_reason": "AI 试图在平台宿主机运行本地脚本，必须人工确认。",
            "readonly_block_patterns": [
                r"\brm\b",
                r"\bmkdir\b",
                r"\bmv\b",
                r"\bcp\b",
                r"\bvi\b",
                r"\bvim\b",
                r"\bnano\b",
                r"\bchmod\b",
                r"\bchown\b",
                r"\bdd\b",
                r"\bdel\b",
                r"\bformat\b",
                r"\brmdir\b",
                r">",
                r">>",
            ],
            "hard_block_substrings": [
                "del /f /s /q",
                "format ",
                "shutdown ",
                "rmdir /s",
                "taskkill /f /im svchost",
                "rm -rf /",
                "mkfs.",
                "dd if=",
                ":(){ :|:& };:",
                "> /dev/sd",
                "shutdown -h",
                "halt",
                "poweroff",
                "init 0",
            ],
        },
        "skill_change": {
            "always_approval": True,
            "approval_reason": "AI 试图创建或修改平台技能，必须人工审批并审计。",
            "hard_block_substrings": [
                "../",
                "..\\",
                "\x00",
            ],
        },
        "linux": {
            "hard_block_substrings": [
                "rm -rf /",
                "mkfs.",
                "dd if=",
                ":(){ :|:& };:",
                "> /dev/sd",
                "init 0",
            ],
            "approval_patterns": [
                r"\brm\b",
                r"\bmkdir\b",
                r"\bmv\b",
                r"\bcp\b",
                r"\btee\b",
                r"\bchmod\b",
                r"\bchown\b",
                r"\bdd\b",
                r"\bmkfs\b",
                r"\bfdisk\b",
                r"\bparted\b",
                r"\bmount\b",
                r"\bumount\b",
                r"\bsysctl\s+-w\b",
                r"\bcrontab\s+(-e|-r)\b",
                r"\buser(add|del|mod)\b",
                r"\bgroup(add|del|mod)\b",
                r"\bsystemctl\s+(start|stop|restart|enable|disable|mask|unmask)\b",
                r"\bservice\s+\S+\s+(start|stop|restart)\b",
                r"\byum\s+(install|remove|erase|update|upgrade)\b",
                r"\bdnf\s+(install|remove|erase|update|upgrade)\b",
                r"\bapt(-get)?\s+(install|remove|purge|update|upgrade)\b",
                r"\bzypper\s+(install|remove|update)\b",
                r"\brpm\s+-[eUi]\b",
                r"\bkill\b",
                r"\bpkill\b",
                r"\breboot\b",
                r"\bshutdown\b",
                r"\biptables\b",
                r"\bfirewall-cmd\b",
                r"\bdocker\s+(rm|rmi|run|stop|start|restart|exec|cp|compose\s+(up|down|restart))\b",
                r"\bkubectl\s+(apply|delete|patch|scale|replace|create|edit|rollout\s+restart)\b",
                r">",
                r">>",
            ],
            "readonly_block_patterns": [
                r"\brm\b",
                r"\bmkdir\b",
                r"\bmv\b",
                r"\bcp\b",
                r"\btee\b",
                r"\bchmod\b",
                r"\bchown\b",
                r"\bdd\b",
                r"\bmkfs\b",
                r"\bfdisk\b",
                r"\bparted\b",
                r"\bsysctl\s+-w\b",
                r"\bcrontab\s+(-e|-r)\b",
                r"\buser(add|del|mod)\b",
                r"\bgroup(add|del|mod)\b",
                r"\bsystemctl\s+(start|stop|restart|enable|disable|mask|unmask)\b",
                r"\byum\s+(install|remove|erase|update|upgrade)\b",
                r"\bdnf\s+(install|remove|erase|update|upgrade)\b",
                r"\bapt(-get)?\s+(install|remove|purge|update|upgrade)\b",
                r"\brpm\s+-[eUi]\b",
                r"\breboot\b",
                r"\bshutdown\b",
                r">",
                r">>",
            ],
            "readonly_safe_roots": [
                "awk",
                "cat",
                "crontab",
                "date",
                "df",
                "dig",
                "dmesg",
                "dpkg",
                "docker",
                "du",
                "env",
                "find",
                "free",
                "grep",
                "head",
                "hostname",
                "id",
                "ifconfig",
                "iostat",
                "ip",
                "journalctl",
                "kubectl",
                "less",
                "lsof",
                "lsblk",
                "lscpu",
                "lsmem",
                "mpstat",
                "netstat",
                "ps",
                "pwd",
                "printenv",
                "rpm",
                "sar",
                "sed",
                "ss",
                "stat",
                "sysctl",
                "systemd-analyze",
                "systemctl",
                "tail",
                "top",
                "uptime",
                "vmstat",
                "which",
                "who",
                "whoami",
                "whereis",
            ],
            "readonly_unknown_requires_approval": False,
        },
        "windows": {
            "hard_block_substrings": [
                "del /f /s /q",
                "format ",
                "rmdir /s",
                "taskkill /f /im svchost",
            ],
            "approval_patterns": [
                r"\bRemove-",
                r"\bSet-(Item|ItemProperty|Service|ExecutionPolicy|LocalUser|LocalGroup|NetFirewall|Acl|Content)\b",
                r"\bNew-(Item|Service|LocalUser|LocalGroup|NetFirewallRule)\b",
                r"\bRename-Item\b",
                r"\bMove-Item\b",
                r"\bCopy-Item\b",
                r"\bClear-Content\b",
                r"\bAdd-Content\b",
                r"\bOut-File\b",
                r"\bRestart-",
                r"\bStop-",
                r"\bStart-Service\b",
                r"\bStop-Service\b",
                r"\bRestart-Service\b",
                r"\bSet-ItemProperty\b",
                r"\bNew-Item\b",
                r"\bRemove-Item\b",
                r"\btaskkill\b",
                r"\bshutdown\b",
                r"\bRestart-Computer\b",
                r"\bdel\b",
                r"\brmdir\b",
                r"\bformat\b",
                r"\bsc\s+(start|stop|delete|config)\b",
                r"\breg\s+(add|delete|import)\b",
                r"\bnet\s+(user|localgroup)\b",
            ],
            "readonly_block_patterns": [
                r"\bRemove-",
                r"\bSet-(Item|ItemProperty|Service|ExecutionPolicy|LocalUser|LocalGroup|NetFirewall|Acl|Content)\b",
                r"\bNew-(Item|Service|LocalUser|LocalGroup|NetFirewallRule)\b",
                r"\bRename-Item\b",
                r"\bMove-Item\b",
                r"\bCopy-Item\b",
                r"\bClear-Content\b",
                r"\bAdd-Content\b",
                r"\bOut-File\b",
                r"\bRestart-",
                r"\bStop-",
                r"\btaskkill\b",
                r"\bshutdown\b",
                r"\bRestart-Computer\b",
                r"\bdel\b",
                r"\brmdir\b",
                r"\bformat\b",
                r"\bsc\s+(start|stop|delete|config)\b",
                r"\breg\s+(add|delete|import)\b",
            ],
        },
        "sql": {
            "hard_block_substrings": [
                "drop database",
                "drop schema",
            ],
            "approval_patterns": [
                r"\binsert\b",
                r"\bupdate\b",
                r"\bdelete\b",
                r"\bdrop\b",
                r"\balter\b",
                r"\btruncate\b",
                r"\breplace\b",
                r"\bmerge\b",
                r"\bcreate\b",
                r"\bgrant\b",
                r"\brevoke\b",
                r"\bcommit\b",
                r"\brollback\b",
                r"\bexec(ute)?\b",
                r"\bcall\b",
            ],
            "readonly_block_patterns": [
                r"\binsert\b",
                r"\bupdate\b",
                r"\bdelete\b",
                r"\bdrop\b",
                r"\balter\b",
                r"\btruncate\b",
                r"\breplace\b",
                r"\bmerge\b",
                r"\bcreate\b",
                r"\bgrant\b",
                r"\brevoke\b",
                r"\bcommit\b",
                r"\brollback\b",
                r"\bexec(ute)?\b",
                r"\bcall\b",
            ],
        },
        "redis": {
            "hard_block_substrings": [
                "flushall",
                "flushdb",
            ],
            "approval_commands": [
                "acl",
                "append",
                "config",
                "del",
                "expire",
                "flushall",
                "flushdb",
                "hdel",
                "hset",
                "incr",
                "lpop",
                "lpush",
                "mset",
                "persist",
                "rename",
                "restore",
                "rpop",
                "rpush",
                "sadd",
                "set",
                "slaveof",
                "unlink",
                "zadd",
            ],
            "readonly_block_commands": [
                "acl",
                "append",
                "config",
                "del",
                "expire",
                "flushall",
                "flushdb",
                "hdel",
                "hset",
                "incr",
                "lpop",
                "lpush",
                "mset",
                "persist",
                "rename",
                "restore",
                "rpop",
                "rpush",
                "sadd",
                "set",
                "slaveof",
                "unlink",
                "zadd",
            ],
        },
        "http": {
            "hard_block_substrings": [],
            "approval_methods": ["POST", "PUT", "PATCH", "DELETE"],
            "readonly_block_methods": ["PUT", "PATCH", "DELETE"],
        },
        "network": {
            "hard_block_substrings": [
                "delete /unreserved",
                "reset saved-configuration",
                "format flash",
            ],
            "approval_patterns": [
                r"\bsystem-view\b",
                r"\bconfigure\b",
                r"\bconf\s+t\b",
                r"\binterface\b",
                r"\bundo\b",
                r"\bshutdown\b",
                r"\breboot\b",
                r"\breset\b",
                r"\bdelete\b",
                r"\bsave\b",
                r"\bcopy\b",
                r"\bwrite\b",
                r"\btftp\b",
                r"\bftp\b",
            ],
            "readonly_block_patterns": [
                r"\bsystem-view\b",
                r"\bconfigure\b",
                r"\bconf\s+t\b",
                r"\binterface\b",
                r"\bundo\b",
                r"\bshutdown\b",
                r"\breboot\b",
                r"\breset\b",
                r"\bdelete\b",
                r"\bsave\b",
                r"\bcopy\b",
                r"\bwrite\b",
                r"\btftp\b",
                r"\bftp\b",
            ],
            "readonly_unknown_requires_approval": False,
        },
    },
}


TOOL_CATEGORY = {
    "local_execute_script": "local",
    "evolve_skill": "skill_change",
    "linux_execute_command": "linux",
    "container_execute_command": "linux",
    "middleware_execute_command": "linux",
    "storage_execute_command": "linux",
    "network_cli_execute_command": "network",
    "execute_on_scope": "linux",
    "winrm_execute_command": "windows",
    "db_execute_query": "sql",
    "redis_execute_command": "redis",
    "mongodb_find": "mongodb",
    "http_api_request": "http",
    "k8s_api_request": "http",
    "monitoring_api_query": "http",
    "virtualization_api_request": "http",
    "storage_api_request": "http",
    "snmp_get": "snmp",
}


def _deep_merge(default: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(default)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    rules: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        decision = str(item.get("decision") or "").strip().lower()
        if decision not in {"allow", "approval", "deny"}:
            continue
        matchers = []
        for matcher in item.get("matchers", []):
            if not isinstance(matcher, dict):
                continue
            matcher_type = str(matcher.get("type") or "").strip().lower()
            matcher_value = str(matcher.get("value") or "").strip()
            if matcher_type and matcher_value:
                matchers.append({"type": matcher_type, "value": matcher_value})
        if not matchers:
            continue
        rules.append(
            {
                "id": str(item.get("id") or f"rule-{index}"),
                "name": str(item.get("name") or "未命名规则"),
                "domain": str(item.get("domain") or ""),
                "platform": str(item.get("platform") or ""),
                "category": str(item.get("category") or ""),
                "resource": str(item.get("resource") or ""),
                "action": str(item.get("action") or ""),
                "decision": decision,
                "description": str(item.get("description") or ""),
                "enabled": bool(item.get("enabled", True)),
                "scope": item.get("scope") if isinstance(item.get("scope"), dict) else {"type": "all", "value": ""},
                "sources": _string_list(item.get("sources", [])),
                "matchers": matchers,
            }
        )
    return rules


def validate_safety_policy(policy: dict[str, Any]) -> list[str]:
    """Return user-facing validation errors for editable safety policy rules."""
    issues: list[str] = []
    categories = policy.get("categories", {})
    if isinstance(categories, dict):
        for category_name, cfg in categories.items():
            if not isinstance(cfg, dict):
                continue
            for field in ("approval_patterns", "readonly_block_patterns"):
                for index, pattern in enumerate(_string_list(cfg.get(field, [])), start=1):
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        issues.append(f"{category_name}.{field} 第 {index} 行正则无效: {exc}")

    for rule in policy.get("rules", []):
        for matcher in rule.get("matchers", []):
            if matcher.get("type") != "regex":
                continue
            try:
                re.compile(str(matcher.get("value") or ""))
            except re.error as exc:
                issues.append(f"{rule.get('name') or rule.get('id')}: 正则无效: {exc}")
    return issues


def normalize_safety_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _deep_merge(DEFAULT_SAFETY_POLICY, policy or {})
    normalized["version"] = 1
    try:
        timeout = int(normalized.get("approval_timeout_seconds", 300))
    except (TypeError, ValueError):
        timeout = 300
    normalized["approval_timeout_seconds"] = max(30, min(timeout, 1800))
    normalized["readwrite_chat_warning_enabled"] = bool(
        normalized.get("readwrite_chat_warning_enabled", True)
    )
    normalized["rules"] = _normalize_rules(normalized.get("rules", []))

    categories = normalized.setdefault("categories", {})
    for name, cfg in list(categories.items()):
        if not isinstance(cfg, dict):
            categories[name] = {}
            cfg = categories[name]
        cfg["approval_patterns"] = _string_list(cfg.get("approval_patterns", []))
        cfg["readonly_block_patterns"] = _string_list(cfg.get("readonly_block_patterns", []))
        cfg["readonly_safe_roots"] = [item.lower() for item in _string_list(cfg.get("readonly_safe_roots", []))]
        cfg["approval_commands"] = [item.lower() for item in _string_list(cfg.get("approval_commands", []))]
        cfg["readonly_block_commands"] = [item.lower() for item in _string_list(cfg.get("readonly_block_commands", []))]
        cfg["approval_methods"] = [item.upper() for item in _string_list(cfg.get("approval_methods", []))]
        cfg["readonly_block_methods"] = [item.upper() for item in _string_list(cfg.get("readonly_block_methods", []))]
        cfg["hard_block_substrings"] = [item.lower() for item in _string_list(cfg.get("hard_block_substrings", []))]
        cfg["always_approval"] = bool(cfg.get("always_approval", False))
        if "readonly_unknown_requires_approval" in cfg:
            cfg["readonly_unknown_requires_approval"] = bool(cfg["readonly_unknown_requires_approval"])
        if "approval_reason" in cfg:
            cfg["approval_reason"] = str(cfg["approval_reason"])
    return normalized


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


def _cmd_root(command: str) -> str:
    stripped = command.strip()
    if not stripped:
        return ""
    return stripped.split()[0].strip().lower()


def _regex_matches(patterns: list[str], text: str) -> bool:
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def _semantic_text(tool_call_name: str, args: dict[str, Any]) -> str:
    parts = [
        _command_text(tool_call_name, args),
        str(args.get("method") or ""),
        str(args.get("path") or ""),
        str(args.get("oid") or ""),
        " ".join(_platform_actions(tool_call_name, args)),
    ]
    return " ".join(part for part in parts if part).strip()


def _platform_actions(tool_call_name: str, args: dict[str, Any]) -> list[str]:
    method = str(args.get("method") or "GET").upper()
    path = str(args.get("path") or "").lower()
    body_text = json.dumps(args.get("body") or {}, ensure_ascii=False).lower()
    actions: list[str] = []

    if tool_call_name == "k8s_api_request":
        if method == "DELETE" and "/namespaces/" in path:
            actions.append("k8s.delete_namespace")
        if method in {"PATCH", "PUT", "POST"} and "deployments" in path and ("scale" in path or "replicas" in body_text):
            actions.append("k8s.scale_deployment")
        if method == "DELETE" and "/pods/" in path:
            actions.append("k8s.delete_pod")
        if method in {"PATCH", "PUT", "POST"} and ("secrets" in path or "rbac" in path):
            actions.append("k8s.modify_sensitive_resource")

    if tool_call_name == "virtualization_api_request":
        if method == "DELETE" and any(token in path for token in ("vm", "server", "instance")):
            actions.append("virtualization.delete_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("reboot", "restart", "reset")):
            actions.append("virtualization.reboot_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("migrate", "relocate")):
            actions.append("virtualization.migrate_vm")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("snapshot", "rollback", "revert")):
            actions.append("virtualization.snapshot_or_rollback")

    if tool_call_name == "storage_api_request":
        is_bucket_root = path.count("/") <= 1 and bool(path.strip("/"))
        if method == "GET" and not path.endswith("/"):
            actions.append("s3.download_object")
        if method == "DELETE" and is_bucket_root:
            actions.append("s3.delete_bucket")
        if method == "DELETE" and not is_bucket_root:
            actions.append("s3.delete_object")
        if method in {"PUT", "PATCH", "POST"} and any(token in path for token in ("policy", "acl", "publicaccessblock")):
            actions.append("s3.change_bucket_policy")
            if "public" in body_text or "publicaccessblock" in path:
                actions.append("s3.public_bucket")

    if tool_call_name == "monitoring_api_query":
        if method == "POST" and "silence" in path:
            actions.append("monitoring.create_silence")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("ruler", "rules", "alert")):
            actions.append("monitoring.modify_rule")
        if method == "DELETE" and any(token in path for token in ("ruler", "rules", "alert")):
            actions.append("monitoring.delete_rule")

    return actions


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
        return lower_value in _platform_actions("", {}) or lower_value in lower_text
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
            "asset_group": str(context.get("target_scope") or context.get("scope_value") or context.get("group_name") or "").lower(),
            "tag": " ".join(tags),
            "environment": str(context.get("environment") or "").lower(),
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


def check_approval_needed(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    policy = get_safety_policy()
    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "该动作需要人工审批。")

    cfg = _category(tool_call_name, policy)
    if not cfg:
        return False, ""

    if cfg.get("always_approval"):
        return True, cfg.get("approval_reason") or "该工具调用需要人工审批。"

    if tool_call_name == "http_api_request":
        method = str(args.get("method") or "GET").upper()
        if method in cfg.get("approval_methods", []):
            return True, f"HTTP {method} 可能改变目标系统状态，需要确认。"
        return False, ""

    if tool_call_name == "redis_execute_command":
        root = _cmd_root(_command_text(tool_call_name, args))
        if root in cfg.get("approval_commands", []):
            return True, "检测到 Redis 写操作或高危命令。"
        return False, ""

    command = _command_text(tool_call_name, args)
    if _regex_matches(cfg.get("approval_patterns", []), command):
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
    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context, {"approval"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "只读会话不执行需要审批的变更动作。")

    cfg = _category(tool_call_name, policy)
    if not cfg:
        return False, ""

    if tool_call_name == "http_api_request":
        method = str(args.get("method") or "GET").upper()
        if method in cfg.get("readonly_block_methods", []):
            return True, f"只读安全模式，已拦截 HTTP {method} 请求"
        return False, ""

    if tool_call_name == "redis_execute_command":
        root = _cmd_root(_command_text(tool_call_name, args))
        if root in cfg.get("readonly_block_commands", []):
            return True, "只读安全模式，已拦截潜在的 Redis 修改动作"
        return False, ""

    command = _command_text(tool_call_name, args)
    if _regex_matches(cfg.get("readonly_block_patterns", []), command):
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
    semantic_rule = _matched_semantic_rule(policy, tool_call_name, args, context or {}, {"deny"})
    if semantic_rule:
        return True, _rule_reason(semantic_rule, "该动作被配置为禁止执行。")

    cfg = _category(tool_call_name, policy)
    command = _command_text(tool_call_name, args).lower()
    for marker in cfg.get("hard_block_substrings", []):
        if marker and marker in command:
            return True, "指令触发硬拦截策略，已被系统拒绝。"
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

    hard_blocked, hard_reason = check_hard_block(tool_call_name, args, ctx)
    checks.append(
        {
            "name": "禁止执行",
            "matched": hard_blocked,
            "reason": hard_reason,
        }
    )
    if hard_blocked:
        return {
            "decision": "deny",
            "label": "禁止执行",
            "mode": mode,
            "reason": hard_reason,
            "checks": checks,
        }

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
        return {
            "decision": "readonly_block",
            "label": "只读保护阻止",
            "mode": mode,
            "reason": readonly_reason,
            "checks": checks,
        }

    if needs_approval:
        return {
            "decision": "approval",
            "label": "需要审批",
            "mode": mode,
            "reason": approval_reason,
            "checks": checks,
        }

    return {
        "decision": "allow",
        "label": "允许执行",
        "mode": mode,
        "reason": "未命中审批或禁止执行规则。",
        "checks": checks,
    }
