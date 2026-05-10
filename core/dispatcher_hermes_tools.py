"""Dispatcher bridge for Hermes-backed agent environment tools."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from core.hermes_tool_adapter import HERMES_AGENT_TOOL_NAMES, execute_hermes_tool


HERMES_DISPATCH_TOOL_NAMES = HERMES_AGENT_TOOL_NAMES - {"clarify", "web_search"}
BROWSER_TOOL_NAMES = {name for name in HERMES_DISPATCH_TOOL_NAMES if name.startswith("browser_")}


def _timeout_from_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(5.0, value)


def hermes_tool_timeout_seconds(tool_call_name: str) -> float:
    if tool_call_name in BROWSER_TOOL_NAMES:
        return _timeout_from_env("OPSCORE_HERMES_BROWSER_TIMEOUT_SECONDS", 45.0)
    return _timeout_from_env("OPSCORE_HERMES_TOOL_TIMEOUT_SECONDS", 120.0)


async def execute_hermes_dispatch_tool(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    if tool_call_name not in HERMES_DISPATCH_TOOL_NAMES:
        return json.dumps(
            {
                "status": "ERROR",
                "tool": tool_call_name,
                "error": "Hermes tool is not enabled for OpsCore agent dispatch.",
            },
            ensure_ascii=False,
        )
    timeout_seconds = hermes_tool_timeout_seconds(tool_call_name)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(execute_hermes_tool, tool_call_name, args, context),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        log.warning("Hermes tool timed out: %s after %.1fs", tool_call_name, timeout_seconds)
        return json.dumps(
            {
                "status": "ERROR",
                "tool": tool_call_name,
                "error_type": "timeout",
                "error": f"{tool_call_name} timed out after {timeout_seconds:.0f}s.",
                "hint": "浏览器或外部页面没有及时返回；请换一个可信来源继续，或向用户说明该来源不可访问。",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        log.exception("Hermes tool failed: %s", tool_call_name)
        return json.dumps(
            {
                "status": "ERROR",
                "tool": tool_call_name,
                "error": f"{type(exc).__name__}: {exc}",
            },
            ensure_ascii=False,
        )
