from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Callable

from core import memory as memory_module
from core.session_history import build_session_history_markdown as build_session_history_markdown_content
from core.session_webhook import (
    SessionWebhookError,
    build_session_webhook_payload,
    post_webhook,
    validate_webhook_url,
    webhook_payload_preview,
)


class SessionWebhookServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


SUPPORTED_PAYLOAD_TYPES = {"profile", "summary", "markdown"}
SUPPORTED_CHANNELS = {"generic", "wechat", "dingtalk"}


def _resolve_memory_db(memory_db: Any | None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def normalize_session_webhook_options(payload_type: str | None, channel: str | None) -> tuple[str, str]:
    normalized_payload_type = str(payload_type or "profile").lower()
    if normalized_payload_type not in SUPPORTED_PAYLOAD_TYPES:
        raise SessionWebhookServiceError(422, "payload_type 仅支持 profile、summary、markdown。")

    normalized_channel = str(channel or "generic").lower()
    if normalized_channel not in SUPPORTED_CHANNELS:
        raise SessionWebhookServiceError(422, "channel 仅支持 generic、wechat、dingtalk。")

    return normalized_payload_type, normalized_channel


def resolve_session_webhook_target(url: str, allow_private_targets: bool = False) -> tuple[str, dict]:
    try:
        return validate_webhook_url(url, allow_private_targets)
    except SessionWebhookError as exc:
        raise SessionWebhookServiceError(exc.status_code, exc.detail) from exc


async def build_session_webhook_markdown(
    active_sessions: Mapping[str, dict],
    session_id: str,
    payload_type: str,
    model_name: str | None = None,
    memory_db: Any | None = None,
) -> tuple[str, dict | None]:
    from core.session_profile import generate_session_profile, get_session_profile, profile_to_markdown

    resolved_memory_db = _resolve_memory_db(memory_db)
    if payload_type == "markdown":
        markdown = await asyncio.to_thread(
            build_session_history_markdown_content,
            resolved_memory_db,
            active_sessions,
            session_id,
        )
        return markdown, None

    profile = await asyncio.to_thread(get_session_profile, session_id)
    if not profile:
        profile = await generate_session_profile(session_id, model_name=model_name, include_inspection=False)

    profile_markdown = profile_to_markdown(profile)
    if payload_type == "profile":
        return profile_markdown, profile

    history_markdown = await asyncio.to_thread(
        build_session_history_markdown_content,
        resolved_memory_db,
        active_sessions,
        session_id,
    )
    summary = history_markdown[:1800] if history_markdown else "当前会话暂无可发送的聊天摘要。"
    return f"{profile_markdown}\n\n## 会话摘要\n\n{summary}", profile


def ensure_session_webhook_markdown(markdown: str) -> None:
    if not str(markdown or "").strip():
        raise SessionWebhookServiceError(404, "当前会话没有可发送内容。")


async def preview_session_webhook_delivery(
    active_sessions: Mapping[str, dict],
    *,
    session_id: str,
    webhook_url: str,
    payload_type: str | None = "profile",
    channel: str | None = "generic",
    title: str | None = None,
    model_name: str | None = None,
    allow_private_targets: bool = False,
    memory_db: Any | None = None,
) -> dict[str, Any]:
    _, target = resolve_session_webhook_target(webhook_url, allow_private_targets)
    normalized_payload_type, normalized_channel = normalize_session_webhook_options(payload_type, channel)
    markdown, profile = await build_session_webhook_markdown(
        active_sessions,
        session_id,
        normalized_payload_type,
        model_name,
        memory_db=memory_db,
    )
    ensure_session_webhook_markdown(markdown)

    resolved_title = title or f"OpsCore 会话报告 {session_id}"
    payload = build_session_webhook_payload(
        session_id,
        normalized_payload_type,
        normalized_channel,
        resolved_title,
        markdown,
        profile,
    )
    return {
        "target": target,
        "payload_type": normalized_payload_type,
        "channel": normalized_channel,
        "title": resolved_title,
        "payload": webhook_payload_preview(payload),
    }


def _webhook_delivery_record(
    *,
    session_id: str,
    target: dict[str, Any],
    channel: str,
    payload_type: str,
    title: str,
    status: str,
    http_status: int | None,
    response_preview: str = "",
    error: str = "",
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "webhook_host": target["host"],
        "channel": channel,
        "payload_type": payload_type,
        "title": title,
        "status": status,
        "http_status": http_status,
        "response_preview": response_preview[:300],
        "error": error[:500],
    }


async def send_session_webhook_delivery(
    active_sessions: Mapping[str, dict],
    *,
    session_id: str,
    webhook_url: str,
    payload_type: str | None = "profile",
    channel: str | None = "generic",
    title: str | None = None,
    model_name: str | None = None,
    allow_private_targets: bool = False,
    memory_db: Any | None = None,
    poster: Callable[[str, dict], tuple[int, str]] = post_webhook,
) -> dict[str, Any]:
    webhook_url, target = resolve_session_webhook_target(webhook_url, allow_private_targets)
    normalized_payload_type, normalized_channel = normalize_session_webhook_options(payload_type, channel)
    resolved_memory_db = _resolve_memory_db(memory_db)
    markdown, profile = await build_session_webhook_markdown(
        active_sessions,
        session_id,
        normalized_payload_type,
        model_name,
        memory_db=resolved_memory_db,
    )
    ensure_session_webhook_markdown(markdown)

    resolved_title = title or f"OpsCore 会话报告 {session_id}"
    payload = build_session_webhook_payload(
        session_id,
        normalized_payload_type,
        normalized_channel,
        resolved_title,
        markdown,
        profile,
    )

    try:
        status_code, response_body = await asyncio.to_thread(poster, webhook_url, payload)
        await asyncio.to_thread(
            resolved_memory_db.append_webhook_delivery,
            _webhook_delivery_record(
                session_id=session_id,
                target=target,
                channel=normalized_channel,
                payload_type=normalized_payload_type,
                title=resolved_title,
                status="success" if status_code < 400 else "error",
                http_status=status_code,
                response_preview=response_body,
                error="" if status_code < 400 else f"HTTP {status_code}",
            ),
        )
    except Exception as exc:
        await asyncio.to_thread(
            resolved_memory_db.append_webhook_delivery,
            _webhook_delivery_record(
                session_id=session_id,
                target=target,
                channel=normalized_channel,
                payload_type=normalized_payload_type,
                title=resolved_title,
                status="error",
                http_status=None,
                error=str(exc),
            ),
        )
        raise

    if status_code >= 400:
        raise SessionWebhookServiceError(502, f"Webhook 返回 HTTP {status_code}: {response_body[:300]}")

    return {
        "http_status": status_code,
        "response_preview": response_body[:300],
        "target": target,
    }


async def list_session_webhook_delivery_records(
    session_id: str,
    limit: int = 10,
    memory_db: Any | None = None,
) -> list[dict]:
    try:
        return await asyncio.to_thread(
            _resolve_memory_db(memory_db).list_webhook_deliveries,
            session_id,
            limit,
        )
    except Exception as exc:
        raise SessionWebhookServiceError(500, str(exc)) from exc
