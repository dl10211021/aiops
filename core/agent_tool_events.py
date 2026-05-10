from __future__ import annotations

import json
from dataclasses import dataclass

from core.redaction import redact_json_text, redact_text


@dataclass(frozen=True)
class PreparedToolCall:
    id: str
    name: str
    args: dict
    parse_error: str | None
    display_cmd: str


def summarize_tool_result_for_sse(tool_result, preview_limit: int = 300) -> dict:
    """Return a redacted UI preview plus small structured metadata for tool traces."""
    if isinstance(tool_result, (dict, list)):
        raw_text = json.dumps(tool_result, ensure_ascii=False, default=str)
    else:
        raw_text = str(tool_result or "")
    safe_text = redact_json_text(raw_text)
    preview = (
        safe_text[:preview_limit] + "..."
        if len(safe_text) > preview_limit
        else safe_text
    )
    status = "done"
    metadata = {}

    try:
        parsed = json.loads(safe_text)
    except Exception:
        parsed = None

    if isinstance(parsed, dict):
        raw_status = str(parsed.get("status") or "").upper()
        if raw_status in {"ERROR", "FAILED", "BLOCKED"}:
            status = "error"
            metadata["status"] = raw_status
        if parsed.get("success") is False or parsed.get("has_error") is True:
            status = "error"
        if parsed.get("error") or parsed.get("reason"):
            status = "error"
        if parsed.get("reason"):
            metadata["reason"] = parsed.get("reason")
        if parsed.get("error"):
            metadata["error"] = parsed.get("error")

        for key in (
            "statement_type",
            "has_result_set",
            "committed",
            "affected_rows",
            "count",
            "message",
            "error_type",
            "hint",
            "raw_error",
            "exit_status",
            "has_error",
            "stderr",
        ):
            value = parsed.get(key)
            if value is not None:
                metadata[key] = value
        if parsed.get("actions"):
            metadata["actions"] = parsed.get("actions")
        if parsed.get("primary_action"):
            metadata["primary_action"] = parsed.get("primary_action")
        if parsed.get("policy_decision"):
            metadata["policy_decision"] = parsed.get("policy_decision")
        if metadata:
            if "statement_type" in metadata or "has_result_set" in metadata:
                metadata["type"] = "database_statement"
            else:
                metadata["type"] = "tool_result"
    elif '"BLOCKED"' in safe_text or '"ERROR"' in safe_text or "错误：" in safe_text:
        status = "error"

    return {
        "safe_text": safe_text,
        "preview": preview,
        "status": status,
        "metadata": metadata,
    }


def build_tool_end_event(
    tool_call_id: str,
    tool_name: str,
    tool_result,
) -> tuple[str, str]:
    result_summary = summarize_tool_result_for_sse(tool_result)
    message = json.dumps(
        {
            "type": "tool_end",
            "id": tool_call_id,
            "tool": tool_name,
            "result": result_summary["preview"],
            "result_status": result_summary["status"],
            "result_meta": result_summary["metadata"],
        },
        ensure_ascii=False,
    )
    return message, result_summary["safe_text"]


def parse_tool_arguments(raw_arguments) -> dict:
    """Parse model tool arguments, with a repair fallback for complex shell snippets."""
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if raw_arguments is None:
        return {}

    raw_text = str(raw_arguments or "").strip()
    if not raw_text:
        return {}

    try:
        parsed = json.loads(raw_text)
    except Exception as strict_error:
        try:
            from json_repair import loads as repair_json_loads

            parsed = repair_json_loads(raw_text)
        except Exception:
            raise strict_error

    if isinstance(parsed, dict):
        return parsed
    return {}


def prepare_tool_call(tool_call: dict) -> PreparedToolCall:
    tool_name = tool_call.get("function", {}).get("name", "")
    parse_error = None
    try:
        tool_args = parse_tool_arguments(
            tool_call.get("function", {}).get("arguments", "{}")
        )
    except Exception as e:
        tool_args = {}
        parse_error = str(e)

    display_cmd = redact_text(_display_tool_arguments(tool_args))
    if parse_error:
        display_cmd = "JSON解析失败: " + parse_error

    return PreparedToolCall(
        id=tool_call.get("id", ""),
        name=tool_name,
        args=tool_args,
        parse_error=parse_error,
        display_cmd=display_cmd,
    )


def _display_tool_arguments(tool_args: dict) -> str:
    """Return the operation the user cares about for trace display."""
    command = tool_args.get("command")
    if isinstance(command, str) and command.strip():
        return command.strip()

    sql = tool_args.get("sql")
    if isinstance(sql, str) and sql.strip():
        return sql.strip()

    method = tool_args.get("method")
    path = tool_args.get("path") or tool_args.get("url") or tool_args.get("endpoint")
    if isinstance(method, str) and isinstance(path, str) and method.strip() and path.strip():
        return f"{method.strip().upper()} {path.strip()}"

    action = tool_args.get("action") or tool_args.get("operation")
    if isinstance(action, str) and action.strip():
        return action.strip()

    return json.dumps(tool_args, ensure_ascii=False, default=str)


def invalid_tool_arguments_result(parse_error: str) -> str:
    return json.dumps(
        {
            "status": "ERROR",
            "error_type": "tool_arguments_invalid",
            "error": f"参数 JSON 格式无效，请检查是否包含未转义字符或格式错误: {parse_error}",
            "hint": "请重新生成工具参数，复杂 PowerShell/SQL 片段需要正确转义。",
        },
        ensure_ascii=False,
    )
