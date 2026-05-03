"""SQLite-backed custom slash command storage."""

from __future__ import annotations

import datetime
import sqlite3
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Lock
from typing import Any


class SlashCommandStore:
    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        lock: Lock,
    ):
        self._connect = connect
        self._lock = lock

    def list_slash_commands(self) -> list[dict]:
        with self._lock, self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, label, description, prompt_template, category, scope_type,
                       asset_type, protocol, host, readonly, pinned, enabled, sort_order,
                       created_at, updated_at
                FROM slash_commands
                ORDER BY pinned DESC, sort_order ASC, label ASC
                """
            ).fetchall()
            return [slash_command_row(row) for row in rows]

    def save_slash_command(self, command: dict) -> dict:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        command_id = str(command.get("id") or "").strip()
        if not command_id:
            command_id = f"custom-{int(time.time() * 1000)}"
        payload = {
            "id": command_id,
            "label": str(command.get("label") or "").strip(),
            "description": str(command.get("description") or "").strip(),
            "prompt_template": str(command.get("prompt_template") or "").strip(),
            "category": str(command.get("category") or "自定义").strip() or "自定义",
            "scope_type": str(command.get("scope_type") or "global").strip() or "global",
            "asset_type": str(command.get("asset_type") or "").strip().lower(),
            "protocol": str(command.get("protocol") or "").strip().lower(),
            "host": str(command.get("host") or "").strip().lower(),
            "readonly": 1 if command.get("readonly", True) else 0,
            "pinned": 1 if command.get("pinned", False) else 0,
            "enabled": 1 if command.get("enabled", True) else 0,
            "sort_order": max(1, min(100, int(command.get("sort_order") or 1))),
        }
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO slash_commands
                    (id, label, description, prompt_template, category, scope_type,
                     asset_type, protocol, host, readonly, pinned, enabled, sort_order,
                     created_at, updated_at)
                VALUES
                    (:id, :label, :description, :prompt_template, :category, :scope_type,
                     :asset_type, :protocol, :host, :readonly, :pinned, :enabled, :sort_order,
                     :now, :now)
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    description = excluded.description,
                    prompt_template = excluded.prompt_template,
                    category = excluded.category,
                    scope_type = excluded.scope_type,
                    asset_type = excluded.asset_type,
                    protocol = excluded.protocol,
                    host = excluded.host,
                    readonly = excluded.readonly,
                    pinned = excluded.pinned,
                    enabled = excluded.enabled,
                    sort_order = excluded.sort_order,
                    updated_at = excluded.updated_at
                """,
                {**payload, "now": now},
            )
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, label, description, prompt_template, category, scope_type,
                       asset_type, protocol, host, readonly, pinned, enabled, sort_order,
                       created_at, updated_at
                FROM slash_commands WHERE id = ?
                """,
                (command_id,),
            ).fetchone()
            return slash_command_row(row)

    def delete_slash_command(self, command_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM slash_commands WHERE id = ?", (command_id,))
            return cursor.rowcount > 0


def slash_command_row(row: Any) -> dict:
    return {
        "id": row["id"],
        "label": row["label"],
        "description": row["description"] or "",
        "prompt_template": row["prompt_template"],
        "category": row["category"] or "自定义",
        "scope_type": row["scope_type"] or "global",
        "asset_type": row["asset_type"] or "",
        "protocol": row["protocol"] or "",
        "host": row["host"] or "",
        "readonly": bool(row["readonly"]),
        "pinned": bool(row["pinned"]),
        "enabled": bool(row["enabled"]),
        "sort_order": max(1, min(100, int(row["sort_order"] or 1))),
        "source": "custom",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
