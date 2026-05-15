from __future__ import annotations

from core.tool_display import tool_label
from core.tool_trace_policy import trace_evidence_id, trace_tool_policy


def chat_history_messages(messages: list[dict]) -> list[dict]:
    return [msg for msg in messages if msg.get("role") in ("user", "assistant")]


def format_attachment_lines(attachments: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        details = [
            str(item.get("ext") or item.get("kind") or "附件"),
            f"{item.get('size')} bytes" if item.get("size") is not None else "",
            f"{item.get('rows')} 行" if item.get("rows") is not None else "",
            f"{item.get('pages')} 页" if item.get("pages") is not None else "",
            "已截断" if item.get("truncated") else "",
        ]
        lines.append(
            f"- {item.get('filename') or 'attachment'}"
            + f" ({'；'.join(part for part in details if part)})"
        )
    return lines


def _record_value(record: dict | None, key: str) -> str:
    if not isinstance(record, dict):
        return ""
    value = record.get(key)
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return ""


def _operation_label(mode: str) -> str:
    return {
        "read": "只读",
        "write": "写入",
        "read_write": "读写受控",
        "destructive": "破坏性",
        "external_effect": "外发",
        "interactive": "人工交互",
    }.get(mode, mode or "")


def _approval_label(policy: str) -> str:
    return {
        "none": "无需审批",
        "guarded_write": "写入受控",
        "always_required": "强制审批",
    }.get(policy, policy or "")


def _evidence_label(family: str) -> str:
    return {
        "database": "数据库证据",
        "host_cli": "主机命令证据",
        "http_api": "HTTP/API 证据",
        "observability": "可观测证据",
        "network": "网络证据",
        "storage": "存储证据",
        "virtualization": "虚拟化证据",
        "container": "容器证据",
        "knowledge": "知识证据",
        "notification": "通知审计",
        "memory": "记忆审计",
        "human_interaction": "人工输入",
        "local_runtime": "本地运行时",
        "platform": "平台证据",
    }.get(family, family or "")


def _format_policy_line(policy: dict) -> str:
    parts = [
        _operation_label(_record_value(policy, "operation_mode")),
        _approval_label(_record_value(policy, "approval_policy")),
        _evidence_label(_record_value(policy, "evidence_family")),
    ]
    if _record_value(policy, "destructive").lower() == "true":
        parts.append("破坏性")
    return "；".join(part for part in parts if part)


def _format_runtime_line(item: dict) -> str:
    result_meta = item.get("resultMeta") or item.get("result_meta") or {}
    if not isinstance(result_meta, dict):
        return ""
    runtime = result_meta.get("runtime_execution") or result_meta.get("runtime_policy")
    if not isinstance(runtime, dict):
        return ""
    parts: list[str] = []
    final_status = _record_value(runtime, "final_status")
    error_type = _record_value(runtime, "error_type")
    timeout_seconds = _record_value(runtime, "timeout_seconds")
    if final_status == "error":
        if error_type == "tool_timeout" and timeout_seconds:
            parts.append(f"实际超时 {timeout_seconds}s")
        else:
            parts.append("实际执行失败")
    if _record_value(runtime, "retried").lower() != "true":
        return "；".join(parts)
    attempts = _record_value(runtime, "attempts")
    max_attempts = _record_value(runtime, "max_attempts")
    if not attempts:
        return "；".join(parts)
    total = f"/{max_attempts}" if max_attempts else ""
    parts.append(f"实际重试 {attempts}{total} 次")
    return "；".join(parts)


def format_exec_trace_lines(exec_trace: list[dict]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(exec_trace or [], start=1):
        if not isinstance(item, dict):
            continue
        tool = item.get("tool") or "unknown"
        label = tool_label(str(tool))
        tool_text = f"{label} (`{tool}`)" if label != tool else f"`{tool}`"
        status = item.get("status") or "done"
        args = str(item.get("args") or "").strip()
        result = str(item.get("result") or "").strip()
        lines.append(f"- Step {index}: {tool_text} [{status}]")
        policy_line = _format_policy_line(trace_tool_policy(item, str(tool)))
        if policy_line:
            lines.append(f"  - Policy: {policy_line}")
        runtime_line = _format_runtime_line(item)
        if runtime_line:
            lines.append(f"  - Runtime: {runtime_line}")
        evidence_id = trace_evidence_id(item)
        if evidence_id:
            lines.append(f"  - Evidence: {evidence_id}")
        if args:
            lines.append(f"  - Execute: {args}")
        if result:
            lines.append(f"  - Result: {result}")
    return lines


def format_session_history_markdown(messages: list[dict], title: str) -> str:
    chat_history = chat_history_messages(messages)
    if not chat_history:
        return ""

    md_lines = [f"# Chat History: {title}\n"]
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "AI Assistant"
        attachment_lines = format_attachment_lines(msg.get("attachments") or [])
        attachment_block = (
            "\n\n### Attachments\n" + "\n".join(attachment_lines)
            if attachment_lines
            else ""
        )
        trace_lines = format_exec_trace_lines(
            msg.get("exec_trace") or msg.get("execTrace") or []
        )
        trace_block = (
            "\n\n### AI Execution Trace\n" + "\n".join(trace_lines)
            if trace_lines
            else ""
        )
        md_lines.append(f"## {role}\n{msg['content']}{attachment_block}{trace_block}\n\n---\n")
    return "\n".join(md_lines)
