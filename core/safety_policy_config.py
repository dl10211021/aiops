from __future__ import annotations

import ipaddress
import re
from copy import deepcopy
from typing import Any

from core.safety_action_catalog import DEFAULT_ACTION_RULES

DEFAULT_SAFETY_POLICY: dict[str, Any] = {
    "version": 1,
    "approval_timeout_seconds": 300,
    "readwrite_chat_warning_enabled": True,
    "rules": [],
    "action_rules": deepcopy(DEFAULT_ACTION_RULES),
    "network_boundary": {
        "enabled": False,
        "active_cidrs": [],
        "readonly_cidrs": [],
        "blocked_cidrs": [],
        "allowed_hosts": [],
        "blocked_hosts": [],
        "block_unknown_targets": False,
    },
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
                r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:/sbin/)?reboot\b",
                r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:/sbin/)?shutdown\b",
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
                r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:/sbin/)?reboot\b",
                r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:/sbin/)?shutdown\b",
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
                "findmnt",
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
                "last",
                "less",
                "lsof",
                "blkid",
                "lsblk",
                "lscpu",
                "lsmem",
                "mount",
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
                "drop user",
                "drop tablespace",
                "shutdown immediate",
                "startup mount",
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
        "memcached": {
            "hard_block_substrings": [
                "flush_all",
            ],
            "approval_commands": [
                "add",
                "append",
                "cas",
                "decr",
                "delete",
                "flush_all",
                "gat",
                "gats",
                "incr",
                "prepend",
                "replace",
                "set",
                "touch",
            ],
            "readonly_block_commands": [
                "add",
                "append",
                "cas",
                "decr",
                "delete",
                "flush_all",
                "gat",
                "gats",
                "incr",
                "prepend",
                "replace",
                "set",
                "touch",
            ],
        },
        "mongodb": {
            "hard_block_substrings": [
                "dropdatabase",
                "drop database",
                "dropcollection",
                "drop collection",
            ],
            "approval_commands": [
                "aggregate",
                "insert",
                "update",
                "replace",
                "delete",
                "createindex",
                "dropindex",
                "createuser",
                "dropuser",
                "grantroles",
                "replset",
                "sh",
            ],
            "readonly_block_commands": [
                "aggregate",
                "insert",
                "update",
                "replace",
                "delete",
                "createindex",
                "dropindex",
                "createuser",
                "dropuser",
                "grantroles",
                "replset",
                "sh",
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
    boundary = policy.get("network_boundary", {})
    if isinstance(boundary, dict):
        for field in ("active_cidrs", "readonly_cidrs", "blocked_cidrs"):
            for item in _string_list(boundary.get(field, [])):
                try:
                    ipaddress.ip_network(item, strict=False)
                except ValueError as exc:
                    issues.append(f"network_boundary.{field} 网段无效 {item}: {exc}")
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
    action_rules = normalized.get("action_rules")
    if not isinstance(action_rules, dict):
        action_rules = {}
        normalized["action_rules"] = action_rules
    for domain, rules in list(action_rules.items()):
        if not isinstance(rules, dict):
            action_rules[domain] = {}
            continue
        action_rules[domain] = {
            str(action_id).strip(): str(decision).strip().lower()
            for action_id, decision in rules.items()
            if str(action_id).strip() and str(decision).strip().lower() in {"allow", "approval", "deny"}
        }
    boundary = normalized.get("network_boundary")
    if not isinstance(boundary, dict):
        boundary = {}
    normalized["network_boundary"] = {
        "enabled": bool(boundary.get("enabled", False)),
        "active_cidrs": _string_list(boundary.get("active_cidrs", [])),
        "readonly_cidrs": _string_list(boundary.get("readonly_cidrs", [])),
        "blocked_cidrs": _string_list(boundary.get("blocked_cidrs", [])),
        "allowed_hosts": [item.lower() for item in _string_list(boundary.get("allowed_hosts", []))],
        "blocked_hosts": [item.lower() for item in _string_list(boundary.get("blocked_hosts", []))],
        "block_unknown_targets": bool(boundary.get("block_unknown_targets", False)),
    }

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
