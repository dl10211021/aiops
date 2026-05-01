import json
import os
import ipaddress
import re
import shlex
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from core.safety_action_catalog import (
    ACTION_PRIORITY as _ACTION_PRIORITY,
    DEFAULT_ACTION_RULES,
    action_detail,
)


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
POLICY_PATH = os.path.join(ROOT_DIR, "safety_policy.json")

_SHELL_NOOP_REDIRECTION_RE = re.compile(
    r"(?:(?<=\s)|^)(?:[0-9]?>>?|&>)\s*/dev/null\b"
    r"|(?:(?<=\s)|^)[0-9]?>&[0-9]\b"
)


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
    "memcached_execute_command": "memcached",
    "mongodb_find": "mongodb",
    "http_api_request": "http",
    "database_api_request": "http",
    "bigdata_api_request": "http",
    "middleware_api_request": "http",
    "discovery_api_request": "http",
    "container_api_request": "http",
    "network_api_request": "http",
    "security_api_request": "http",
    "cicd_api_request": "http",
    "ai_platform_api_request": "http",
    "oob_api_request": "http",
    "k8s_api_request": "http",
    "monitoring_api_query": "http",
    "virtualization_api_request": "http",
    "storage_api_request": "http",
    "service_probe_request": "http",
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


def _compact_sql(sql: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", str(sql or ""), flags=re.DOTALL)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(re.sub(r"--.*$", "", line))
    return re.sub(r"\s+", " ", " ".join(lines)).strip().lower()


def _sql_actions(sql: str) -> list[str]:
    text = _compact_sql(sql)
    if not text:
        return []
    root = text.split(None, 1)[0]
    actions: list[str] = []

    if root in {"select", "show", "describe", "desc", "explain", "with"}:
        actions.append("sql.read")
    if root in {"insert", "update", "delete", "merge", "replace", "call"}:
        actions.append("sql.data_write")
    if root in {"create", "alter", "drop", "truncate", "rename"}:
        actions.append("sql.schema_change")
    if root in {"grant", "revoke"} or re.search(r"\b(create|alter|drop)\s+user\b", text):
        actions.append("sql.privilege_change")
    if re.search(r"\balter\s+system\b|\bswitch\s+logfile\b|\bshutdown\b|\bstartup\b|\bcheckpoint\b", text):
        actions.append("sql.instance_admin")
    if root in {"commit", "rollback"}:
        actions.append("sql.transaction")
    if re.search(r"\bdrop\s+(database|schema|user|tablespace)\b|\btruncate\s+table\b", text):
        actions.append("sql.dangerous_drop")
    return actions


def _sql_action_summary(sql: str) -> tuple[str, str]:
    actions = set(_sql_actions(sql))
    if "sql.dangerous_drop" in actions:
        return "数据库高危删除", "检测到删库、删用户、删表空间或清表动作，属于高危不可逆操作。"
    if "sql.instance_admin" in actions:
        return "数据库实例管理", "检测到数据库实例级管理动作，例如日志切换、实例启停或检查点，需要人工确认。"
    if "sql.privilege_change" in actions:
        return "数据库账号权限变更", "检测到数据库账号或权限变更动作，需要人工确认影响范围。"
    if "sql.schema_change" in actions:
        return "数据库结构变更", "检测到数据库表结构、对象或索引变更动作，需要人工确认。"
    if "sql.data_write" in actions:
        return "数据库数据写入", "检测到 INSERT、UPDATE、DELETE、MERGE 或过程调用等数据写入动作，需要人工确认。"
    if "sql.transaction" in actions:
        return "数据库事务控制", "检测到 COMMIT 或 ROLLBACK 等事务控制动作，需要确认当前事务上下文。"
    return "数据库变更", "检测到数据库数据修改或结构变更操作。"


def _strip_sudo(tokens: list[str]) -> list[str]:
    if tokens and tokens[0] == "sudo":
        return tokens[1:]
    return tokens


def _command_segments(command: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(r"\s*(?:&&|\|\||;|\|)\s*", _policy_match_text("linux_execute_command", {"command": command}))
        if segment.strip()
    ]


def _has_file_write_redirect(command: str) -> bool:
    text = _policy_match_text("linux_execute_command", {"command": command})
    return bool(re.search(r"(?:(?<=\s)|^)(?:[0-9]?>>?|&>)\s*(?!/dev/null\b)\S+", text))


def _contains_sensitive_path(command: str) -> bool:
    lower = command.lower()
    sensitive_markers = (
        "/etc/shadow",
        "/etc/gshadow",
        "/root/.ssh",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        ".pem",
        ".key",
    )
    return any(marker in lower for marker in sensitive_markers)


def _contains_filesystem_read_path(command: str) -> bool:
    lower = command.lower()
    markers = (
        "/etc/fstab",
        "/proc/mounts",
        "/proc/self/mounts",
        "/proc/swaps",
        "/sys/block/",
        "/sys/class/block/",
    )
    return any(marker in lower for marker in markers)


def _tokenize_segment(segment: str) -> list[str]:
    try:
        return [token.lower() for token in shlex.split(segment, posix=True)]
    except ValueError:
        return segment.lower().split()


def classify_linux_actions(command: str) -> list[str]:
    actions: list[str] = []
    if not str(command or "").strip():
        return actions

    if _has_file_write_redirect(command):
        actions.append("linux.file.write")

    for segment in _command_segments(command):
        tokens = _strip_sudo(_tokenize_segment(segment))
        if not tokens:
            continue
        root = tokens[0].split("/")[-1]

        if root in {"reboot", "shutdown", "poweroff", "halt"} or (root == "init" and len(tokens) > 1 and tokens[1] in {"0", "6"}):
            actions.append("linux.system.power")
            continue

        if root == "systemctl":
            verb = next((token for token in tokens[1:] if not token.startswith("-")), "")
            if verb in {"status", "show", "cat", "list-units", "list-unit-files", "is-active", "is-enabled", "is-failed"}:
                actions.append("linux.read.service")
            elif verb in {"start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask", "daemon-reload"}:
                actions.append("linux.service.change")
            continue

        if root == "service":
            verb = tokens[2] if len(tokens) > 2 else ""
            if verb in {"status", "--status-all"}:
                actions.append("linux.read.service")
            elif verb in {"start", "stop", "restart", "reload"}:
                actions.append("linux.service.change")
            continue

        if root in {"free", "df", "du", "lscpu", "lsmem", "uptime", "top", "vmstat", "iostat", "mpstat", "sar", "uname", "hostname", "date", "id", "whoami", "who", "env", "printenv"}:
            actions.append("linux.read.resource")
            continue

        if root in {"lsblk", "blkid", "findmnt"}:
            actions.append("linux.read.filesystem")
            continue

        if root == "mount":
            option_tokens = [token for token in tokens[1:] if token.startswith("-")]
            positional_tokens = [token for token in tokens[1:] if not token.startswith("-")]
            read_only_options = {"-l", "-v", "-h", "--help", "--version", "--show-labels"}
            if not tokens[1:] or (option_tokens and all(token in read_only_options for token in option_tokens) and not positional_tokens):
                actions.append("linux.read.filesystem")
            else:
                actions.append("linux.disk.change")
            continue

        if root == "swapon" and any(token in {"--show", "-s", "--summary"} for token in tokens[1:]):
            actions.append("linux.read.filesystem")
            continue

        if root in {"journalctl", "dmesg"}:
            actions.append("linux.read.logs")
            continue

        if root in {"cat", "tail", "head", "less", "grep", "awk", "sed", "find", "stat"}:
            if _contains_sensitive_path(segment):
                actions.append("linux.sensitive.read")
            elif _contains_filesystem_read_path(segment):
                actions.append("linux.read.filesystem")
            elif "/var/log" in segment.lower():
                actions.append("linux.read.logs")
            else:
                actions.append("linux.read.file")
            continue

        if root == "crontab":
            if any(token in {"-e", "-r"} for token in tokens[1:]):
                actions.append("linux.file.write")
            else:
                actions.append("linux.read.cron")
            continue

        if root == "last":
            actions.append("linux.read.history")
            continue

        if root == "ip":
            if any(token in {"add", "del", "delete", "replace", "set", "flush"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "route":
            if any(token in {"add", "del", "delete", "change"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "ifconfig":
            if any(token in {"up", "down", "netmask", "broadcast", "mtu"} for token in tokens[1:]):
                actions.append("linux.network.change")
            else:
                actions.append("linux.read.network")
            continue

        if root == "firewall-cmd":
            if any(token.startswith("--list") or token in {"--state", "--get-active-zones", "--get-default-zone"} for token in tokens[1:]):
                actions.append("linux.read.network")
            else:
                actions.append("linux.network.change")
            continue

        if root == "nft":
            if any(token in {"list", "show"} for token in tokens[1:]):
                actions.append("linux.read.network")
            else:
                actions.append("linux.network.change")
            continue

        if root in {"ss", "netstat", "lsof", "dig", "nslookup", "host"}:
            actions.append("linux.read.network")
            continue

        if root in {"ping", "curl", "wget", "nc", "ncat", "netcat", "nmap", "telnet", "traceroute", "tracepath", "ssh", "scp", "sftp", "rsync"}:
            actions.append("linux.network.probe")
            continue

        if root in {"rm", "rmdir", "unlink"}:
            actions.append("linux.file.delete")
            continue
        if root in {"touch", "mkdir", "mv", "cp", "tee", "vi", "vim", "nano"}:
            actions.append("linux.file.write")
            continue
        if root in {"chmod", "chown", "chgrp", "setfacl"}:
            actions.append("linux.permission.change")
            continue
        if root in {"useradd", "userdel", "usermod", "groupadd", "groupdel", "groupmod", "passwd"}:
            actions.append("linux.user.change")
            continue
        if root in {"yum", "dnf", "apt", "apt-get", "zypper", "rpm"} and any(token in {"install", "remove", "erase", "update", "upgrade", "purge", "-e", "-u", "-i"} for token in tokens[1:]):
            actions.append("linux.package.change")
            continue
        if root in {"dd", "mkfs", "fdisk", "parted", "umount", "swapon", "swapoff"}:
            actions.append("linux.disk.change")
            continue
        if root in {"iptables"}:
            actions.append("linux.network.change")
            continue

    seen: set[str] = set()
    return [action for action in actions if not (action in seen or seen.add(action))]


def _contains_windows_sensitive_path(command: str) -> bool:
    lower = command.lower()
    sensitive_markers = (
        r"\windows\system32\config\sam",
        r"\windows\system32\config\system",
        r"\windows\system32\config\security",
        r"\ntds\ntds.dit",
        "ntds.dit",
        "lsass.dmp",
        "unattend.xml",
        "sysprep.inf",
        r"\microsoft\crypto\rsa\machinekeys",
        r"\appdata\roaming\microsoft\protect",
        r"\appdata\roaming\microsoft\crypto",
    )
    return any(marker in lower for marker in sensitive_markers)


def classify_windows_actions(command: str) -> list[str]:
    """Classify high-confidence PowerShell/CMD actions for WinRM sessions."""
    text = re.sub(r"\s+", " ", str(command or "")).strip()
    lower = text.lower()
    if not lower:
        return []

    actions: list[str] = []

    def add(action: str) -> None:
        actions.append(action)

    if re.search(r"\b(get-ciminstance|get-wmiobject|get-computerinfo|systeminfo|get-hotfix|hostname|whoami)\b", lower):
        add("windows.read.info")
    if re.search(r"\b(get-service)\b|\bsc(?:\.exe)?\s+query\b", lower):
        add("windows.read.service")
    if re.search(r"\b(get-winevent|get-eventlog)\b", lower):
        add("windows.read.eventlog")
    if re.search(r"\b(get-process|tasklist)\b", lower):
        add("windows.read.process")
    if re.search(r"\b(get-net\w*|get-dnsclient\w*|get-nettcpconnection|get-netroute|get-netip\w*|ipconfig|netstat)\b|\broute\s+print\b", lower):
        add("windows.read.network")
    if re.search(r"\b(get-content|type|cat)\b", lower):
        add("windows.read.file")
        if _contains_windows_sensitive_path(lower):
            add("windows.sensitive.read")
    if re.search(r"\b(get-vm|get-vmhost|get-vmswitch|get-vmnetworkadapter|get-vmharddiskdrive|get-vmreplication|get-vmsnapshot)\b", lower):
        add("windows.read.virtualization")

    if re.search(r"\b(test-netconnection|tnc|invoke-webrequest|iwr|invoke-restmethod|irm|ping|curl|wget|nslookup|tracert|resolve-dnsname)\b", lower):
        add("windows.network.probe")

    if re.search(r"\b(restart-computer|stop-computer|shutdown)\b", lower):
        add("windows.system.power")
    if re.search(r"\b(start-service|stop-service|restart-service|set-service|new-service|remove-service)\b|\bsc(?:\.exe)?\s+(start|stop|delete|config)\b", lower):
        add("windows.service.change")
    if re.search(r"\b(stop-process)\b|\btaskkill\b", lower):
        add("windows.process.stop")
    if re.search(r"\b(remove-item)\b|(?:^|[\s;&|])(?:del|erase|rmdir|rd)(?:\s|$)", lower):
        add("windows.file.delete")
    if re.search(r"\b(new-item|set-content|add-content|clear-content|out-file|copy-item|move-item|rename-item)\b", lower):
        add("windows.file.write")
    if re.search(r"\b(set-acl|get-acl\s*\|\s*set-acl|icacls)\b", lower):
        add("windows.permission.change")
    if re.search(r"\b(new-localuser|set-localuser|remove-localuser|new-localgroup|set-localgroup|remove-localgroup|add-localgroupmember|remove-localgroupmember)\b|\bnet\s+(user|localgroup)\b", lower):
        add("windows.user.change")
    if re.search(r"\b(new-itemproperty|set-itemproperty|remove-itemproperty|set-executionpolicy)\b|\breg(?:\.exe)?\s+(add|delete|import)\b", lower):
        add("windows.registry.change")
    if re.search(r"\b(new-netfirewallrule|set-netfirewallrule|remove-netfirewallrule|enable-netfirewallrule|disable-netfirewallrule)\b|\bnetsh\s+advfirewall\b", lower):
        add("windows.firewall.change")
    if re.search(r"\b(install-windowsfeature|uninstall-windowsfeature|install-module|uninstall-module|install-package|uninstall-package|winget|choco|msiexec)\b", lower):
        add("windows.package.change")

    if re.search(r"\b(start-vm|stop-vm|restart-vm|suspend-vm|resume-vm|save-vm)\b", lower):
        add("hyperv.vm.power")
    if re.search(r"\b(new-vm|set-vm|checkpoint-vm|restore-vmsnapshot|move-vm|set-vmnetworkadapter|set-vmharddiskdrive)\b", lower):
        add("hyperv.vm.change")
    if re.search(r"\b(remove-vm)\b", lower):
        add("hyperv.vm.delete")

    seen: set[str] = set()
    return [action for action in actions if not (action in seen or seen.add(action))]


def _datastore_root(command: str) -> str:
    try:
        parts = shlex.split(str(command or "").strip(), posix=True)
    except ValueError:
        parts = str(command or "").strip().split()
    return parts[0].lower() if parts else ""


def classify_redis_actions(command: str) -> list[str]:
    root = _datastore_root(command)
    if not root:
        return []
    if root in {"get", "mget", "hget", "hgetall", "hmget", "lrange", "llen", "smembers", "scard", "zrange", "zcard", "scan", "sscan", "hscan", "zscan", "info", "dbsize", "ttl", "pttl", "exists", "type", "keys", "client", "cluster", "memory", "slowlog", "monitor"}:
        return ["redis.read"]
    if root in {"flushall", "flushdb"}:
        return ["redis.flush"]
    if root == "acl":
        return ["redis.acl_change"]
    if root == "config" or root in {"module", "script"}:
        return ["redis.config_change"]
    if root in {"save", "bgsave", "bgrewriteaof"}:
        return ["redis.persistence_change"]
    if root in {"replicaof", "slaveof"}:
        return ["redis.replication_change"]
    if root in {"del", "unlink", "rename", "renamenx"}:
        return ["redis.key_delete"]
    if root in {"expire", "pexpire", "expireat", "pexpireat", "persist", "touch"}:
        return ["redis.expire"]
    if root in {"incr", "incrby", "incrbyfloat", "decr", "decrby"}:
        return ["redis.counter_change"]
    if root in {"set", "setex", "psetex", "setnx", "mset", "msetnx", "append", "getset", "hset", "hmset", "hdel", "hincrby", "hincrbyfloat", "lpush", "rpush", "lpop", "rpop", "lset", "ltrim", "sadd", "srem", "spop", "smove", "zadd", "zrem", "zincrby", "restore"}:
        return ["redis.key_write"]
    return []


def classify_memcached_actions(command: str) -> list[str]:
    root = _datastore_root(command)
    if not root:
        return []
    if root in {"version", "stats", "get", "gets"}:
        return ["memcached.read"]
    if root == "flush_all":
        return ["memcached.flush"]
    if root == "delete":
        return ["memcached.key_delete"]
    if root in {"incr", "decr", "touch", "gat", "gats"}:
        return ["memcached.counter_change"]
    if root in {"set", "add", "replace", "append", "prepend", "cas"}:
        return ["memcached.key_write"]
    return []


def classify_mongodb_actions(command: str = "", *, operation: str = "find") -> list[str]:
    root = _datastore_root(operation or command)
    if not root:
        return []
    if root in {"find", "count", "distinct", "listcollections", "listindexes", "stats", "ping"}:
        return ["mongodb.find"]
    if root == "aggregate":
        return ["mongodb.aggregate"]
    if root in {"dropdatabase", "dropcollection", "drop"}:
        return ["mongodb.drop"]
    if root in {"createindex", "dropindex", "createindexes", "dropindexes"}:
        return ["mongodb.index_change"]
    if root in {"createuser", "dropuser", "grantroles", "replset", "sh", "setparameter"}:
        return ["mongodb.admin"]
    if root in {"insert", "insertone", "insertmany", "update", "updateone", "updatemany", "replace", "replaceone", "delete", "deleteone", "deletemany"}:
        return ["mongodb.write"]
    return []


def classify_network_actions(command: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(command or "")).strip()
    lower = text.lower()
    if not lower:
        return []

    actions: list[str] = []

    def add(action: str) -> None:
        if action not in actions:
            actions.append(action)

    root = _cmd_root(lower)
    is_read_command = root in {"show", "display", "dis"}
    if is_read_command:
        if re.search(r"\b(current-configuration|running-config|startup-config|saved-configuration|configuration|current|cur|cu|run|running)\b", lower):
            add("network.read.config")
        else:
            add("network.read.status")
        return actions

    if re.search(r"\b(ping|traceroute|tracert|telnet)\b", lower):
        add("network.diagnostic")
    if re.search(r"\b(system-view|configure terminal|conf t)\b", lower):
        add("network.config.mode")
    if re.search(r"\b(interface|port link-type|switchport|shutdown|undo shutdown|vlan|port access|port trunk|description)\b", lower):
        add("network.interface.change")
    if re.search(r"\b(ip route-static|ip route|route add|route delete|static-route|ip prefix-list|route-policy)\b", lower):
        add("network.route.change")
    if re.search(r"\b(acl|access-list|security-policy|firewall|nat|policy-map|class-map|zone-pair|traffic-filter)\b", lower):
        add("network.acl_nat.change")
    if re.search(r"\b(save|write memory|copy running-config startup-config|copy run start)\b", lower):
        add("network.save_config")
    if re.search(r"\b(tftp|ftp|scp|sftp|copy tftp|copy ftp|copy scp|copy flash)\b", lower):
        add("network.file_transfer")
    if re.search(
        r"\b(reload|reboot|factory-reset|erase startup-config|write erase|reset saved-configuration|reset saved-config|delete /unreserved|format flash|format)\b",
        lower,
    ):
        add("network.reset")
    return actions


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


def _platform_actions(tool_call_name: str, args: dict[str, Any]) -> list[str]:
    method = str(args.get("method") or "GET").upper()
    path = str(args.get("path") or "").lower()
    body_text = json.dumps(args.get("body") or {}, ensure_ascii=False).lower()
    actions: list[str] = []

    if tool_call_name == "k8s_api_request":
        if method == "DELETE" and re.search(r"/namespaces/[^/]+/?$", path):
            actions.append("k8s.delete_namespace")
        if method in {"PATCH", "PUT", "POST"} and "deployments" in path and ("scale" in path or "replicas" in body_text):
            actions.append("k8s.scale_deployment")
        if method == "DELETE" and "/pods/" in path:
            actions.append("k8s.delete_pod")
        if method == "DELETE" and "/secrets/" in path:
            actions.append("k8s.delete_secret")
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
            actions.append("virtualization.rollback_snapshot")

    if tool_call_name == "middleware_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"reload_config", "restart_service"} or any(token in path for token in ("reload", "restart")):
            actions.append("middleware.reload_config")
        if operation in {"publish_config", "update_config"} or ("nacos" in path and method in {"POST", "PUT", "PATCH"} and "config" in path):
            actions.append("nacos.publish_config")
        if operation in {"delete_topic", "remove_topic"} or (method == "DELETE" and "topic" in path):
            actions.append("kafka.delete_topic")

    if tool_call_name == "bigdata_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"kill_application", "cancel_job", "stop_job"} or any(token in path for token in ("kill", "cancel", "stop")):
            actions.append("yarn.kill_application")
        if operation in {"drop_partition", "delete_partition"} or (method == "DELETE" and "partition" in path):
            actions.append("bigdata.delete_partition")

    if tool_call_name == "cicd_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"deploy_prod", "release_prod"} or ("prod" in path and any(token in path for token in ("deploy", "release", "build"))):
            actions.append("cicd.deploy_prod")
        if operation in {"rollback", "app_rollback"} or "rollback" in path:
            actions.append("argocd.rollback")
        if operation in {"delete_artifact", "delete_release"} or (method == "DELETE" and any(token in path for token in ("artifact", "repository", "release"))):
            actions.append("artifact.delete_release")

    if tool_call_name == "ai_platform_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"stop_training_job", "kill_job"} or any(token in path for token in ("stop", "kill", "cancel")):
            actions.append("ai.stop_training_job")
        if operation in {"release_gpu", "free_gpu"} or ("gpu" in path and method in {"POST", "PUT", "PATCH", "DELETE"}):
            actions.append("ai.release_gpu")
        if operation in {"delete_model_version", "delete_model"} or (method == "DELETE" and any(token in path for token in ("model", "version"))):
            actions.append("mlflow.delete_model_version")

    if tool_call_name == "storage_api_request":
        operation = str(args.get("operation") or "").strip().lower()
        if operation in {"download_object", "get_object"}:
            actions.append("s3.download_object")
        if operation in {"delete_bucket", "remove_bucket"}:
            actions.append("s3.delete_bucket")
        if operation in {"delete_object", "remove_object"}:
            actions.append("s3.delete_object")
        if operation in {"put_bucket_policy", "put_bucket_acl", "put_public_access_block"}:
            actions.append("s3.change_bucket_policy")
            if "public" in operation or "public" in body_text:
                actions.append("s3.public_bucket")
        is_bucket_root = path.count("/") <= 1 and bool(path.strip("/"))
        object_path_parts = [part for part in path.split("?", 1)[0].split("/") if part]
        if method == "GET" and len(object_path_parts) >= 2 and "list-type" not in path:
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
            actions.append("alertmanager.create_silence")
        if method in {"POST", "PUT", "PATCH"} and any(token in path for token in ("ruler", "rules", "alert")):
            actions.append("monitoring.modify_rule")
            actions.append("monitoring.update_rule")
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
    category = TOOL_CATEGORY.get(tool_call_name, "")
    if not category:
        return []
    rules = policy.get("action_rules", {}).get(category, {})
    if not isinstance(rules, dict):
        return []
    decisions: list[tuple[str, str]] = []
    for action in sorted(_tool_actions(tool_call_name, args), key=lambda item: _ACTION_PRIORITY.get(item, 100)):
        decision = str(rules.get(action) or "").strip().lower()
        if decision in {"allow", "approval", "deny"}:
            decisions.append((action, decision))
    return decisions


def _action_label(action: str) -> str:
    detail = action_detail(action)
    if detail:
        return str(detail.get("label") or action)
    return action


def _action_reason(action: str, decision: str) -> str:
    label = _action_label(action)
    if action == "sql.instance_admin":
        label = "数据库实例级管理"
    if decision == "deny":
        return f"{label} 已被动作策略设置为禁止执行。"
    if decision == "approval":
        return f"{label} 已被动作策略设置为需要人工审批。"
    return f"{label} 已被动作策略设置为允许。"


def _top_action_decision(policy: dict[str, Any], tool_call_name: str, args: dict[str, Any]) -> tuple[str, str, str]:
    decisions = _action_rule_decisions(policy, tool_call_name, args)
    for action, decision in decisions:
        if decision == "deny":
            return action, decision, _action_reason(action, decision)
    for action, decision in decisions:
        if decision == "approval":
            return action, decision, _action_reason(action, decision)
    if decisions and all(decision == "allow" for _, decision in decisions):
        action = decisions[0][0]
        return action, "allow", _action_reason(action, "allow")
    return "", "", ""


def _host_matches(host: str, hosts: list[str]) -> bool:
    normalized = host.strip().lower()
    if not normalized:
        return False
    return normalized in {item.lower() for item in hosts}


def _ip_in_cidrs(host: str, cidrs: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _normalize_network_target(token: str) -> str:
    candidate = str(token or "").strip().strip("[](){}<>'\".,;")
    if not candidate or candidate.startswith("-"):
        return ""
    if candidate.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
        return ""
    if candidate.isdigit():
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    if parsed.hostname:
        return parsed.hostname
    if "@" in candidate:
        candidate = candidate.rsplit("@", 1)[-1]
    if ":" in candidate and candidate.count(":") == 1:
        host, suffix = candidate.rsplit(":", 1)
        if suffix.isdigit() or "/" in suffix:
            candidate = host
        else:
            return ""
    if "/" in candidate or "=" in candidate:
        return ""
    if re.search(r"[A-Za-z]", candidate) or re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", candidate):
        return candidate
    return ""


_NETWORK_OPTION_VALUE_FLAGS: dict[str, set[str]] = {
    "curl": {"-a", "--user-agent", "-b", "--cookie", "-d", "--data", "--data-raw", "--data-binary", "-e", "--referer", "-h", "--header", "-o", "--output", "-u", "--user", "-x", "--request"},
    "wget": {"--header", "--user", "--password", "--post-data", "--post-file", "-o", "--output-document", "-u", "--user-agent"},
    "ping": {"-c", "-i", "-s", "-t", "-W", "-w"},
    "traceroute": {"-m", "-p", "-q", "-w"},
    "tracert": {"-d", "-h", "-w"},
    "tracepath": {"-m", "-p"},
    "nc": {"-p", "-s", "-w"},
    "ncat": {"-p", "-s", "-w"},
    "netcat": {"-p", "-s", "-w"},
    "nmap": {"-p", "-oA", "-oG", "-oN", "-oX", "-iL", "--exclude", "--script", "-sI"},
    "telnet": {},
}


def _network_command_positional_tokens(root: str, tokens: list[str]) -> list[str]:
    if root in {"scp", "sftp", "rsync"}:
        return [
            token
            for token in tokens[1:]
            if "@" in token or re.match(r"^[A-Za-z0-9_.-]+:", token)
        ]
    if root == "ssh":
        return [token for token in tokens[1:] if not token.startswith("-")]

    value_flags = _NETWORK_OPTION_VALUE_FLAGS.get(root, set())
    positional: list[str] = []
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in value_flags:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        positional.append(token)
    return positional


def _extract_network_command_targets(command: str) -> list[str]:
    target_roots = {
        "curl",
        "wget",
        "ping",
        "nc",
        "ncat",
        "netcat",
        "nmap",
        "telnet",
        "traceroute",
        "tracert",
        "tracepath",
        "ssh",
        "scp",
        "sftp",
        "rsync",
    }
    targets: list[str] = []
    for segment in _command_segments(command):
        tokens = _strip_sudo(_tokenize_segment(segment))
        if not tokens:
            continue
        root = tokens[0].split("/")[-1]
        if root not in target_roots:
            continue
        for token in _network_command_positional_tokens(root, tokens):
            target = _normalize_network_target(token)
            if target:
                targets.append(target)
    return targets


def _extract_network_targets(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    host = str(context.get("host") or "").strip()
    if host:
        targets.append(host)
    for key in ("url", "endpoint", "base_url"):
        value = str(args.get(key) or context.get(key) or "").strip()
        if value:
            parsed = urlparse(value if "://" in value else f"//{value}")
            if parsed.hostname:
                targets.append(parsed.hostname)
    path = str(args.get("path") or "")
    if "://" in path:
        parsed = urlparse(path)
        if parsed.hostname:
            targets.append(parsed.hostname)
    command = str(args.get("command") or "")
    if (
        TOOL_CATEGORY.get(tool_call_name) == "linux"
        and "linux.network.probe" in classify_linux_actions(command)
    ) or (
        TOOL_CATEGORY.get(tool_call_name) == "windows"
        and "windows.network.probe" in classify_windows_actions(command)
    ) or (
        TOOL_CATEGORY.get(tool_call_name) == "network"
        and "network.diagnostic" in classify_network_actions(command)
    ):
        for token in re.findall(r"https?://[^\s'\"<>]+|(?<![\w.-])(?:\d{1,3}\.){3}\d{1,3}(?![\w.-])", command):
            parsed = urlparse(token)
            targets.append(parsed.hostname or token)
        targets.extend(_extract_network_command_targets(command))
    seen: set[str] = set()
    return [target for target in targets if target and not (target.lower() in seen or seen.add(target.lower()))]


def check_network_boundary(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> tuple[bool, str]:
    policy = get_safety_policy()
    boundary = policy.get("network_boundary", {})
    if not boundary.get("enabled", False):
        return False, ""

    active_actions = set(_tool_actions(tool_call_name, args))
    is_active_probe = bool({"linux.network.probe", "windows.network.probe", "network.diagnostic"} & active_actions)
    method = str(args.get("method") or "GET").upper()
    is_http_request = TOOL_CATEGORY.get(tool_call_name) == "http"
    if not is_active_probe and not is_http_request:
        return False, ""

    targets = _extract_network_targets(tool_call_name, args, context)
    if not targets:
        if boundary.get("block_unknown_targets", False):
            return True, "未识别到明确目标地址，不允许主动访问未知目标。"
        return False, ""

    active_cidrs = boundary.get("active_cidrs", [])
    readonly_cidrs = boundary.get("readonly_cidrs", [])
    blocked_cidrs = boundary.get("blocked_cidrs", [])
    allowed_hosts = boundary.get("allowed_hosts", [])
    blocked_hosts = boundary.get("blocked_hosts", [])

    for target in targets:
        lower = target.lower()
        if _host_matches(lower, blocked_hosts) or _ip_in_cidrs(lower, blocked_cidrs):
            return True, f"网络活动边界已禁止访问 {target}。"
        if _host_matches(lower, allowed_hosts) or _ip_in_cidrs(lower, active_cidrs):
            continue
        if _ip_in_cidrs(lower, readonly_cidrs):
            return True, f"{target} 只允许读取已有平台数据，禁止主动连接、探测或变更。"
        if boundary.get("block_unknown_targets", False):
            return True, f"{target} 不在授权网络活动范围内。"

    return False, ""


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
