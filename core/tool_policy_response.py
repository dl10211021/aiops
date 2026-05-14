"""Shared tool policy response payloads."""

from __future__ import annotations

import json

from core.safety_policy import explain_policy_decision
from core.tool_registry import tool_policy_metadata


def blocked_tool_response(tool_call_name: str, args: dict, context: dict, reason: str) -> str:
    metadata = explain_policy_decision(tool_call_name, args, context)
    return json.dumps(
        {
            "status": "BLOCKED",
            "reason": reason,
            "actions": metadata.get("actions") or [],
            "primary_action": metadata.get("primary_action"),
            "policy_decision": metadata.get("decision"),
            "tool_policy": tool_policy_metadata(tool_call_name),
        },
        ensure_ascii=False,
    )
