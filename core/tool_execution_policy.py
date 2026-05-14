from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from core.tool_registry import tool_policy_metadata


@dataclass(frozen=True)
class ToolExecutionGate:
    approval_required: bool
    reason: str
    policy: dict[str, Any]


def evaluate_tool_execution_gate(
    tool_name: str,
    *,
    safety_needs_approval: bool = False,
    safety_reason: str = "",
    policy: dict[str, Any] | None = None,
) -> ToolExecutionGate:
    """Combine registry runtime metadata with the existing safety-policy decision."""
    effective_policy = policy or tool_policy_metadata(tool_name)
    operation_mode = str(effective_policy.get("operation_mode") or "")
    approval_policy = str(effective_policy.get("approval_policy") or "")
    destructive = bool(effective_policy.get("destructive"))

    if destructive or approval_policy == "always_required":
        reason = safety_reason or _policy_gate_reason(effective_policy, "强制审批")
        return ToolExecutionGate(True, reason, effective_policy)

    if operation_mode == "external_effect":
        reason = safety_reason or _policy_gate_reason(effective_policy, "外发动作需要人工确认")
        return ToolExecutionGate(True, reason, effective_policy)

    if safety_needs_approval:
        return ToolExecutionGate(True, safety_reason or "命中安全策略，需要审批", effective_policy)

    return ToolExecutionGate(False, "", effective_policy)


async def execute_with_runtime_policy(
    tool_name: str,
    executor: Callable[[], Awaitable[Any]],
    *,
    policy: dict[str, Any] | None = None,
) -> Any:
    effective_policy = policy or tool_policy_metadata(tool_name)
    timeout_policy = effective_policy.get("timeout_policy") if isinstance(effective_policy.get("timeout_policy"), dict) else {}
    retry_policy = effective_policy.get("retry_policy") if isinstance(effective_policy.get("retry_policy"), dict) else {}
    timeout_seconds = _bounded_timeout_seconds(timeout_policy)
    max_attempts = _positive_int(retry_policy.get("max_attempts"), default=1)
    retry_on = {str(item) for item in retry_policy.get("retry_on") or []}

    attempt = 0
    last_error: BaseException | None = None
    while attempt < max_attempts:
        attempt += 1
        try:
            if timeout_seconds:
                return await asyncio.wait_for(executor(), timeout=timeout_seconds)
            return await executor()
        except asyncio.TimeoutError as exc:
            last_error = exc
            if attempt >= max_attempts or "timeout" not in retry_on:
                return _execution_error_result(
                    tool_name,
                    effective_policy,
                    error_type="tool_timeout",
                    error=f"工具执行超过 {int(timeout_seconds or 0)} 秒，已停止。",
                    attempts=attempt,
                )
        except Exception as exc:
            last_error = exc
            error_type = _classify_exception(exc)
            if attempt >= max_attempts or error_type not in retry_on:
                return _execution_error_result(
                    tool_name,
                    effective_policy,
                    error_type=f"tool_{error_type}",
                    error=str(exc) or exc.__class__.__name__,
                    attempts=attempt,
                )

    return _execution_error_result(
        tool_name,
        effective_policy,
        error_type="tool_execution_failed",
        error=str(last_error) if last_error else "工具执行失败。",
        attempts=attempt,
    )


def _policy_gate_reason(policy: dict[str, Any], fallback: str) -> str:
    label = str(policy.get("label") or policy.get("name") or "工具")
    operation = str(policy.get("operation_mode") or "unknown")
    approval = str(policy.get("approval_policy") or "unknown")
    return f"工具执行策略要求审批：{label}，模式={operation}，审批策略={approval}，原因={fallback}"


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return max(1, default)
    return max(1, parsed)


def _bounded_timeout_seconds(timeout_policy: dict[str, Any]) -> float | None:
    default_seconds = _positive_float(timeout_policy.get("default_seconds"))
    max_seconds = _positive_float(timeout_policy.get("max_seconds"))
    if default_seconds is None:
        return None
    if max_seconds is None:
        return default_seconds
    return min(default_seconds, max_seconds)


def _classify_exception(exc: Exception) -> str:
    text = str(exc).lower()
    if isinstance(exc, (ConnectionError, OSError)):
        return "connection_error"
    if "429" in text or "rate limit" in text or "too many requests" in text:
        return "rate_limit"
    return "execution_error"


def _execution_error_result(
    tool_name: str,
    policy: dict[str, Any],
    *,
    error_type: str,
    error: str,
    attempts: int,
) -> str:
    return json.dumps(
        {
            "status": "ERROR",
            "error_type": error_type,
            "error": error,
            "retry_attempts": attempts,
            "tool": tool_name,
            "tool_policy": policy,
        },
        ensure_ascii=False,
    )
