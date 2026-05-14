"""Validation helpers for runtime tool policy metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from core.tool_registry import ToolDefinition


CONTROLLED_OPERATION_MODES = {"write", "read_write", "destructive", "external_effect"}
ALLOWED_RETRY_REASONS = {"timeout", "connection_error", "rate_limit", "execution_error"}


def validate_tool_runtime_policies(tools: Iterable[ToolDefinition]) -> list[str]:
    issues: list[str] = []
    for tool in tools:
        public = tool.public_dict()
        issues.extend(validate_tool_runtime_policy(tool.name, public))
    return issues


def validate_tool_runtime_policy(tool_name: str, policy: Mapping[str, Any]) -> list[str]:
    operation_mode = policy.get("operation_mode")
    approval_policy = policy.get("approval_policy")
    retry_policy = _mapping(policy.get("retry_policy"))
    timeout_policy = _mapping(policy.get("timeout_policy"))
    issue_prefix = f"{tool_name}:{operation_mode}:{approval_policy}"
    issues: list[str] = []

    if operation_mode in CONTROLLED_OPERATION_MODES and approval_policy == "none":
        issues.append(f"{issue_prefix}:controlled_tool_without_approval")
    if operation_mode in CONTROLLED_OPERATION_MODES and policy.get("concurrency_safe"):
        issues.append(f"{issue_prefix}:controlled_tool_marked_concurrency_safe")
    if operation_mode in CONTROLLED_OPERATION_MODES and retry_policy.get("max_attempts") != 1:
        issues.append(f"{issue_prefix}:controlled_tool_retries_enabled")
    if operation_mode == "destructive":
        if not policy.get("destructive"):
            issues.append(f"{issue_prefix}:destructive_flag_missing")
        if approval_policy != "always_required":
            issues.append(f"{issue_prefix}:destructive_tool_not_always_required")
    if operation_mode == "external_effect" and policy.get("result_store_policy") != "audit_only":
        issues.append(f"{issue_prefix}:external_effect_not_audit_only")
    if operation_mode == "read" and approval_policy != "none":
        issues.append(f"{issue_prefix}:read_tool_requires_unexpected_approval")
    if operation_mode == "interactive" and timeout_policy.get("user_driven") is not True:
        issues.append(f"{issue_prefix}:interactive_tool_not_user_driven")
    if not isinstance(timeout_policy.get("default_seconds"), (int, float)):
        issues.append(f"{issue_prefix}:missing_default_timeout")
    if not isinstance(retry_policy.get("max_attempts"), int):
        issues.append(f"{issue_prefix}:missing_retry_attempts")
    if "delay_seconds" in retry_policy and not isinstance(retry_policy.get("delay_seconds"), (int, float)):
        issues.append(f"{issue_prefix}:invalid_retry_delay")
    retry_on = retry_policy.get("retry_on")
    if retry_on is not None:
        issues.extend(_validate_retry_reasons(issue_prefix, retry_on))

    return issues


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _validate_retry_reasons(issue_prefix: str, retry_on: Any) -> list[str]:
    if not isinstance(retry_on, list):
        return [f"{issue_prefix}:invalid_retry_on"]

    issues: list[str] = []
    for reason in retry_on:
        if not isinstance(reason, str) or reason not in ALLOWED_RETRY_REASONS:
            issues.append(f"{issue_prefix}:invalid_retry_reason:{reason}")
    return issues
