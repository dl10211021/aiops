from __future__ import annotations

import logging
from typing import Any

from core.safety_policy import explain_policy_decision, get_safety_policy, save_safety_policy


logger = logging.getLogger(__name__)


class SafetyPolicyServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def get_safety_policy_record() -> dict[str, Any]:
    return get_safety_policy()


def save_safety_policy_record(policy: dict[str, Any]) -> dict[str, Any]:
    try:
        return save_safety_policy(policy)
    except ValueError as exc:
        raise SafetyPolicyServiceError(422, str(exc)) from exc
    except Exception as exc:
        logger.error("保存安全策略失败: %s", exc)
        raise SafetyPolicyServiceError(500, f"保存安全策略失败: {exc}") from exc


def explain_safety_policy_decision(
    tool_name: str,
    tool_args: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    return explain_policy_decision(tool_name, tool_args, context)
