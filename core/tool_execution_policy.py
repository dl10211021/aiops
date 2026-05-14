from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from core.tool_registry import tool_policy_metadata

MAX_RETRY_ATTEMPTS = 3
MAX_RETRY_DELAY_SECONDS = 5.0
RETRYABLE_ERROR_TYPES = frozenset({"timeout", "connection_error", "rate_limit", "execution_error"})


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
    runtime_stats: dict[str, Any] | None = None,
) -> Any:
    effective_policy = policy or tool_policy_metadata(tool_name)
    timeout_policy = effective_policy.get("timeout_policy") if isinstance(effective_policy.get("timeout_policy"), dict) else {}
    retry_policy = effective_policy.get("retry_policy") if isinstance(effective_policy.get("retry_policy"), dict) else {}
    timeout_seconds = _bounded_timeout_seconds(timeout_policy)
    max_attempts = min(
        _positive_int(retry_policy.get("max_attempts"), default=1),
        MAX_RETRY_ATTEMPTS,
    )
    retry_delay_seconds = _bounded_retry_delay_seconds(retry_policy)
    retry_on = _retry_on_error_types(retry_policy)

    attempt = 0
    last_error: BaseException | None = None
    while attempt < max_attempts:
        attempt += 1
        try:
            if timeout_seconds:
                result = await asyncio.wait_for(executor(), timeout=timeout_seconds)
            else:
                result = await executor()
            _update_runtime_stats(
                runtime_stats,
                attempts=attempt,
                max_attempts=max_attempts,
                retry_delay_seconds=retry_delay_seconds,
                retry_on=retry_on,
                timeout_seconds=timeout_seconds,
                final_status="success",
            )
            return result
        except asyncio.TimeoutError as exc:
            last_error = exc
            if attempt >= max_attempts or "timeout" not in retry_on:
                _update_runtime_stats(
                    runtime_stats,
                    attempts=attempt,
                    max_attempts=max_attempts,
                    retry_delay_seconds=retry_delay_seconds,
                    retry_on=retry_on,
                    timeout_seconds=timeout_seconds,
                    final_status="error",
                    error_type="tool_timeout",
                )
                return _execution_error_result(
                    tool_name,
                    effective_policy,
                    error_type="tool_timeout",
                    error=f"工具执行超过 {_format_seconds(timeout_seconds)} 秒，已停止。",
                    attempts=attempt,
                    max_attempts=max_attempts,
                    retry_on=retry_on,
                    retry_delay_seconds=retry_delay_seconds,
                    timeout_seconds=timeout_seconds,
                )
            await _sleep_before_retry(retry_delay_seconds)
        except Exception as exc:
            last_error = exc
            error_type = _classify_exception(exc)
            if attempt >= max_attempts or error_type not in retry_on:
                _update_runtime_stats(
                    runtime_stats,
                    attempts=attempt,
                    max_attempts=max_attempts,
                    retry_delay_seconds=retry_delay_seconds,
                    retry_on=retry_on,
                    timeout_seconds=timeout_seconds,
                    final_status="error",
                    error_type=f"tool_{error_type}",
                )
                return _execution_error_result(
                    tool_name,
                    effective_policy,
                    error_type=f"tool_{error_type}",
                    error=str(exc) or exc.__class__.__name__,
                    attempts=attempt,
                    max_attempts=max_attempts,
                    retry_on=retry_on,
                    retry_delay_seconds=retry_delay_seconds,
                    timeout_seconds=timeout_seconds,
                )
            await _sleep_before_retry(retry_delay_seconds)

    _update_runtime_stats(
        runtime_stats,
        attempts=attempt,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        retry_on=retry_on,
        timeout_seconds=timeout_seconds,
        final_status="error",
        error_type="tool_execution_failed",
    )
    return _execution_error_result(
        tool_name,
        effective_policy,
        error_type="tool_execution_failed",
        error=str(last_error) if last_error else "工具执行失败。",
        attempts=attempt,
        max_attempts=max_attempts,
        retry_on=retry_on,
        retry_delay_seconds=retry_delay_seconds,
        timeout_seconds=timeout_seconds,
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


def _bounded_retry_delay_seconds(retry_policy: dict[str, Any]) -> float:
    delay_seconds = _positive_float(retry_policy.get("delay_seconds"))
    if delay_seconds is None:
        return 0.0
    return min(delay_seconds, MAX_RETRY_DELAY_SECONDS)


def _format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "0"
    if seconds >= 1:
        return f"{seconds:g}"
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def _retry_on_error_types(retry_policy: dict[str, Any]) -> set[str]:
    retry_on = retry_policy.get("retry_on")
    if not isinstance(retry_on, list):
        return set()
    return {item for item in retry_on if isinstance(item, str) and item in RETRYABLE_ERROR_TYPES}


async def _sleep_before_retry(delay_seconds: float) -> None:
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)


def _update_runtime_stats(
    runtime_stats: dict[str, Any] | None,
    *,
    attempts: int,
    max_attempts: int,
    retry_delay_seconds: float,
    retry_on: set[str],
    timeout_seconds: float | None,
    final_status: str,
    error_type: str | None = None,
) -> None:
    if runtime_stats is None:
        return
    runtime_stats.clear()
    runtime_stats.update(
        {
            "attempts": attempts,
            "max_attempts": max_attempts,
            "retried": attempts > 1,
            "retry_delay_seconds": retry_delay_seconds,
            "retry_on": sorted(retry_on),
            "timeout_seconds": timeout_seconds,
            "final_status": final_status,
        }
    )
    if error_type:
        runtime_stats["error_type"] = error_type


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
    max_attempts: int,
    retry_on: set[str],
    retry_delay_seconds: float,
    timeout_seconds: float | None,
) -> str:
    return json.dumps(
        {
            "status": "ERROR",
            "error_type": error_type,
            "error": error,
            "retry_attempts": attempts,
            "runtime_policy": {
                "attempts": attempts,
                "max_attempts": max_attempts,
                "retry_delay_seconds": retry_delay_seconds,
                "retry_on": sorted(retry_on),
                "timeout_seconds": timeout_seconds,
            },
            "tool": tool_name,
            "tool_policy": policy,
        },
        ensure_ascii=False,
    )
