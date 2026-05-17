"""Shared tool policy response payloads."""

from __future__ import annotations

import json

from core.safety_policy import explain_policy_decision
from core.tool_registry import tool_policy_metadata
from core.tool_trace_policy import (
    trace_command_action_summary,
    trace_http_action_summary,
    trace_sql_action_summary,
)


def _blocked_action_summaries(
    tool_call_name: str,
    args: dict,
    tool_policy: dict,
) -> dict[str, str]:
    result_meta: dict[str, object] = {"tool_policy": tool_policy}
    if args.get("method"):
        result_meta["method"] = args.get("method")
    trace_args: object = args.get("sql") if tool_call_name == "db_execute_query" else args
    trace = {
        "tool": tool_call_name,
        "args": trace_args,
        "resultMeta": result_meta,
    }
    summaries = {
        "sql_action": trace_sql_action_summary(trace),
        "http_action": trace_http_action_summary(trace),
        "command_action": trace_command_action_summary(trace),
    }
    return {key: value for key, value in summaries.items() if value}


def blocked_tool_response(tool_call_name: str, args: dict, context: dict, reason: str) -> str:
    metadata = explain_policy_decision(tool_call_name, args, context)
    tool_policy = tool_policy_metadata(tool_call_name)
    payload = {
        "status": "BLOCKED",
        "reason": reason,
        "actions": metadata.get("actions") or [],
        "primary_action": metadata.get("primary_action"),
        "policy_decision": metadata.get("decision"),
        "tool_policy": tool_policy,
    }
    payload.update(_blocked_action_summaries(tool_call_name, args, tool_policy))
    return json.dumps(
        payload,
        ensure_ascii=False,
    )
