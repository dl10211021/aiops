from __future__ import annotations

from typing import Any

from core.tool_registry import tool_policy_metadata


def trace_result_meta(trace: dict[str, Any]) -> dict[str, Any]:
    result_meta = trace.get("resultMeta") or trace.get("result_meta")
    return result_meta if isinstance(result_meta, dict) else {}


def trace_evidence(trace: dict[str, Any]) -> dict[str, Any]:
    evidence = trace.get("evidence")
    return evidence if isinstance(evidence, dict) else {}


def trace_evidence_id(trace: dict[str, Any]) -> str:
    evidence_id = trace.get("evidenceId") or trace.get("evidence_id")
    if evidence_id:
        return str(evidence_id)
    return str(trace_evidence(trace).get("evidence_id") or "")


def trace_tool_policy(
    trace: dict[str, Any],
    tool_name: str | None = None,
    *,
    fallback_to_registry: bool = True,
) -> dict[str, Any]:
    policy = trace_result_meta(trace).get("tool_policy")
    if isinstance(policy, dict):
        return policy
    evidence_meta = trace_evidence(trace).get("result_meta")
    if isinstance(evidence_meta, dict) and isinstance(evidence_meta.get("tool_policy"), dict):
        return evidence_meta["tool_policy"]
    if not fallback_to_registry:
        return {}
    return tool_policy_metadata(str(tool_name or trace.get("tool") or "unknown"))


def policy_summary(policy: dict[str, Any]) -> str:
    values = [
        str(policy.get("operation_mode") or ""),
        str(policy.get("approval_policy") or ""),
        str(policy.get("evidence_family") or ""),
    ]
    return "/".join(value for value in values if value)


def trace_policy_summary(
    trace: dict[str, Any],
    tool_name: str | None = None,
    *,
    fallback_to_registry: bool = True,
) -> str:
    return policy_summary(
        trace_tool_policy(
            trace,
            tool_name,
            fallback_to_registry=fallback_to_registry,
        )
    )


def trace_runtime_summary(trace: dict[str, Any]) -> str:
    result_meta = trace_result_meta(trace)
    runtime = result_meta.get("runtime_execution") or result_meta.get("runtime_policy")
    if not isinstance(runtime, dict):
        return ""
    parts: list[str] = []
    final_status = str(runtime.get("final_status") or "")
    error_type = str(runtime.get("error_type") or "")
    timeout_seconds = runtime.get("timeout_seconds")
    if final_status == "error":
        parts.append(
            f"timeout:{timeout_seconds}s"
            if error_type == "tool_timeout" and timeout_seconds
            else f"error:{error_type or 'tool_execution_failed'}"
        )
    if runtime.get("retried") is True:
        attempts = runtime.get("attempts")
        max_attempts = runtime.get("max_attempts")
        total = f"/{max_attempts}" if max_attempts else ""
        parts.append(f"retry:{attempts}{total}")
    return ",".join(parts)
