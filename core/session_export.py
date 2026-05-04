from __future__ import annotations


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


def format_exec_trace_lines(exec_trace: list[dict]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(exec_trace or [], start=1):
        if not isinstance(item, dict):
            continue
        tool = item.get("tool") or "unknown"
        status = item.get("status") or "done"
        args = str(item.get("args") or "").strip()
        result = str(item.get("result") or "").strip()
        lines.append(f"- Step {index}: `{tool}` [{status}]")
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
