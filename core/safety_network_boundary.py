from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from core.safety_action_classifiers import (
    _command_segments,
    _strip_sudo,
    _tokenize_segment,
    classify_linux_actions,
    classify_network_actions,
    classify_windows_actions,
)


ToolCategoryMap = dict[str, str]


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


def _extract_network_targets(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    tool_category: ToolCategoryMap,
) -> list[str]:
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
        tool_category.get(tool_call_name) == "linux"
        and "linux.network.probe" in classify_linux_actions(command)
    ) or (
        tool_category.get(tool_call_name) == "windows"
        and "windows.network.probe" in classify_windows_actions(command)
    ) or (
        tool_category.get(tool_call_name) == "network"
        and "network.diagnostic" in classify_network_actions(command)
    ):
        for token in re.findall(r"https?://[^\s'\"<>]+|(?<![\w.-])(?:\d{1,3}\.){3}\d{1,3}(?![\w.-])", command):
            parsed = urlparse(token)
            targets.append(parsed.hostname or token)
        targets.extend(_extract_network_command_targets(command))
    seen: set[str] = set()
    return [target for target in targets if target and not (target.lower() in seen or seen.add(target.lower()))]


def _active_network_actions(
    tool_call_name: str,
    args: dict[str, Any],
    tool_category: ToolCategoryMap,
) -> set[str]:
    command = str(args.get("command") or "")
    category = tool_category.get(tool_call_name)
    if category == "linux":
        return set(classify_linux_actions(command))
    if category == "windows":
        return set(classify_windows_actions(command))
    if category == "network":
        return set(classify_network_actions(command))
    return set()


def check_network_boundary(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    *,
    policy: dict[str, Any],
    tool_category: ToolCategoryMap,
) -> tuple[bool, str]:
    boundary = policy.get("network_boundary", {})
    if not boundary.get("enabled", False):
        return False, ""

    active_actions = _active_network_actions(tool_call_name, args, tool_category)
    is_active_probe = bool({"linux.network.probe", "windows.network.probe", "network.diagnostic"} & active_actions)
    is_http_request = tool_category.get(tool_call_name) == "http"
    if not is_active_probe and not is_http_request:
        return False, ""

    targets = _extract_network_targets(tool_call_name, args, context, tool_category)
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
