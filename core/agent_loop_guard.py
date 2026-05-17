from __future__ import annotations

import json
from typing import Any

from core.redaction import redact_value


class ToolSpinGuard:
    """Detect repeated failed tool calls with the same normalized arguments."""

    def __init__(self, *, max_repeated_failures: int = 2):
        self.max_repeated_failures = max(1, int(max_repeated_failures))
        self._failure_counts: dict[str, int] = {}

    def block_reason(self, tool_name: str, args: dict[str, Any]) -> str:
        count = self._failure_counts.get(self._fingerprint(tool_name, args), 0)
        if count < self.max_repeated_failures:
            return ""
        return (
            "检测到模型反复调用同一工具和参数且持续失败，已停止本次重复调用，"
            "避免进入无效循环。请调整排查路径或补充新证据。"
        )

    def record_result(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        status: str,
        result_meta: dict[str, Any] | None = None,
    ) -> None:
        fingerprint = self._fingerprint(tool_name, args)
        if _is_failure(status, result_meta or {}):
            self._failure_counts[fingerprint] = self._failure_counts.get(fingerprint, 0) + 1
        else:
            self._failure_counts.pop(fingerprint, None)

    def _fingerprint(self, tool_name: str, args: dict[str, Any]) -> str:
        try:
            normalized_args = json.dumps(
                redact_value(args or {}),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        except Exception:
            normalized_args = str(redact_value(args or {}))
        return f"{tool_name}:{normalized_args}"


def _is_failure(status: str, result_meta: dict[str, Any]) -> bool:
    normalized_status = str(status or "").lower()
    if normalized_status in {"error", "failed", "blocked"}:
        return True
    error_type = str(result_meta.get("error_type") or "").lower()
    if error_type:
        return True
    result_status = str(result_meta.get("status") or "").lower()
    return result_status in {"error", "failed", "blocked"}
