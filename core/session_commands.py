from __future__ import annotations

from typing import Any

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
