from __future__ import annotations

import asyncio
import json

from core.dispatcher import dispatcher


def _normalize_interaction_options(options: object) -> list[dict[str, str]]:
    if not isinstance(options, list):
        return []
    normalized = []
    for index, item in enumerate(options[:8]):
        if isinstance(item, dict):
            label = str(
                item.get("label") or item.get("value") or f"选项 {index + 1}"
            ).strip()
            value = str(item.get("value") or label).strip()
            description = str(item.get("description") or "").strip()
        else:
            label = str(item or f"选项 {index + 1}").strip()
            value = label
            description = ""
        if label and value:
            normalized.append(
                {
                    "label": label[:80],
                    "value": value[:500],
                    "description": description[:300],
                }
            )
    return normalized


def _build_interaction_payload(tool_call_id: str, args: dict) -> dict:
    input_type = str(args.get("input_type") or "text").strip().lower()
    if input_type not in {"text", "password", "choice"}:
        input_type = "text"
    options = _normalize_interaction_options(args.get("options"))
    if input_type == "choice" and not options:
        input_type = "text"
    timeout_seconds = args.get("timeout_seconds")
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 300
    timeout_seconds = max(30, min(timeout_seconds, 1800))
    return {
        "type": "user_interaction_request",
        "request_id": tool_call_id,
        "prompt": str(args.get("prompt") or "请补充信息").strip()[:1000],
        "input_type": input_type,
        "options": options,
        "placeholder": str(args.get("placeholder") or "").strip()[:200],
        "required": args.get("required") is not False,
        "timeout_seconds": timeout_seconds,
    }


async def _wait_for_user_interaction(
    tool_call_id: str,
    payload: dict,
    future: asyncio.Future,
) -> tuple[str, str]:
    try:
        result = await asyncio.wait_for(
            future,
            timeout=float(payload["timeout_seconds"]),
        )
        value = str(result.get("value") or "")
        label = str(result.get("label") or "")
        tool_res = json.dumps(
            {
                "status": "success",
                "input_type": payload["input_type"],
                "value": value,
                "label": label,
            },
            ensure_ascii=False,
        )
        safe_value = (
            "******" if payload["input_type"] == "password" and value else value
        )
        safe_tool_res = json.dumps(
            {
                "status": "success",
                "input_type": payload["input_type"],
                "value": safe_value,
                "label": label,
            },
            ensure_ascii=False,
        )
        return tool_res, safe_tool_res
    except asyncio.TimeoutError:
        timeout_res = json.dumps(
            {"status": "timeout", "message": "交互式输入超时，用户未在规定时间内回复。"},
            ensure_ascii=False,
        )
        return timeout_res, timeout_res
    finally:
        dispatcher.pending_interactions.pop(tool_call_id, None)
