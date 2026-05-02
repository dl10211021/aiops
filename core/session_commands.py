from __future__ import annotations

import asyncio
from typing import Any

from core.session_tool_context import build_session_tools_payload_for_session
from core.slash_commands import render_builtin_templates, render_slash_commands


class SessionCommandError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def build_session_commands_response(
    tools_payload: dict[str, Any],
    custom_commands: list[dict[str, Any]],
) -> dict[str, Any]:
    context = tools_payload["context"]
    active_tools = tools_payload.get("active_tools") or []
    commands = render_slash_commands(context, active_tools, custom_commands)
    builtin_commands = render_builtin_templates(context, active_tools, custom_commands)
    return {
        "commands": commands,
        "builtin_commands": builtin_commands,
        "custom_commands": custom_commands,
        "context": context,
    }


async def build_session_commands_payload_for_session(
    active_sessions: dict[str, dict],
    tool_registry,
    memory_db,
    session_id: str,
) -> dict[str, Any]:
    tools_payload = build_session_tools_payload_for_session(
        active_sessions,
        tool_registry,
        session_id,
    )
    custom_commands = await list_custom_slash_command_records(memory_db)
    return build_session_commands_response(tools_payload, custom_commands)


async def list_custom_slash_command_records(memory_db) -> list[dict[str, Any]]:
    return await asyncio.to_thread(list_custom_slash_commands, memory_db)


async def save_custom_slash_command_record(
    memory_db,
    payload: dict[str, Any],
    command_id: str | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(save_custom_slash_command, memory_db, payload, command_id)


async def remove_custom_slash_command_record(memory_db, command_id: str) -> None:
    await asyncio.to_thread(remove_custom_slash_command, memory_db, command_id)


def list_custom_slash_commands(memory_db) -> list[dict[str, Any]]:
    return memory_db.list_slash_commands()


def save_custom_slash_command(
    memory_db,
    payload: dict[str, Any],
    command_id: str | None = None,
) -> dict[str, Any]:
    command = dict(payload)
    if command_id is not None:
        command["id"] = command_id
    return memory_db.save_slash_command(command)


def remove_custom_slash_command(memory_db, command_id: str) -> None:
    deleted = memory_db.delete_slash_command(command_id)
    if not deleted:
        raise SessionCommandError(404, "快捷命令不存在")
