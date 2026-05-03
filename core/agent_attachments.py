from __future__ import annotations


def _chat_image_attachments(attachments: list[dict]) -> list[dict]:
    images: list[dict] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        data_url = str(item.get("data_url") or "")
        content_type = str(item.get("content_type") or "")
        if data_url.startswith("data:image/") or content_type.startswith("image/"):
            images.append(item)
    return images[:5]


def _attachment_metadata_for_memory(attachments: list[dict]) -> list[dict]:
    safe_items: list[dict] = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        safe_items.append(
            {
                "filename": item.get("filename") or "attachment",
                "ext": item.get("ext") or "",
                "size": item.get("size") or 0,
                "kind": item.get("kind") or "document",
                "rows": item.get("rows"),
                "pages": item.get("pages"),
                "sheets": item.get("sheets") or [],
                "truncated": bool(item.get("truncated")),
            }
        )
    return safe_items[:8]


def _safe_user_message_for_memory(user_message: str, attachments: list[dict]) -> dict:
    safe_attachments = _attachment_metadata_for_memory(attachments)
    message = {"role": "user", "content": user_message}
    if safe_attachments:
        message["attachments"] = safe_attachments
    return message


def _model_supports_image_input(model_name: str | None) -> bool:
    name = str(model_name or "").lower()
    return any(
        marker in name
        for marker in (
            "gpt-4o",
            "gpt-4.1",
            "gpt-5",
            "claude-3",
            "claude-4",
            "gemini",
            "vision",
            "vl",
            "llava",
            "qwen-vl",
            "qwen2-vl",
            "qwen2.5-vl",
            "kimi-vl",
        )
    )


def _build_current_user_content(
    user_message: str,
    attachments: list[dict],
    model_name: str | None = None,
):
    image_attachments = _chat_image_attachments(attachments)
    if not image_attachments or not _model_supports_image_input(model_name):
        return user_message
    content = [{"type": "text", "text": user_message}]
    for item in image_attachments:
        data_url = str(item.get("data_url") or "")
        if data_url.startswith("data:image/"):
            content.append({"type": "image_url", "image_url": {"url": data_url}})
    return content if len(content) > 1 else user_message
