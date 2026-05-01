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
        md_lines.append(f"## {role}\n{msg['content']}{attachment_block}\n\n---\n")
    return "\n".join(md_lines)
