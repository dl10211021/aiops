"""SQLite-backed asset inventory storage."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Lock
from typing import Any

from core.asset_protocols import resolve_asset_identity

logger = logging.getLogger(__name__)


class AssetStore:
    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        lock: Lock,
        ensure_assets_protocol_column: Callable[[sqlite3.Connection], None],
        encrypt_secret: Callable[..., Any],
        decrypt_secret: Callable[[Any], Any],
        encrypt_extra_args: Callable[..., dict],
        decrypt_extra_args: Callable[[dict], dict],
    ):
        self._connect = connect
        self._lock = lock
        self._ensure_assets_protocol_column = ensure_assets_protocol_column
        self._encrypt_secret = encrypt_secret
        self._decrypt_secret = decrypt_secret
        self._encrypt_extra_args = encrypt_extra_args
        self._decrypt_extra_args = decrypt_extra_args

    def save_assets_batch(self, items: list[dict]) -> None:
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                for item in items:
                    self._upsert_asset(
                        cursor,
                        {
                            "remark": item["remark"],
                            "host": item["host"],
                            "port": item["port"],
                            "username": item["username"],
                            "password": item.get("password"),
                            "asset_type": item.get("asset_type"),
                            "protocol": item.get("protocol")
                            or item.get("login_protocol"),
                            "agent_profile": item["agent_profile"],
                            "extra_args": item.get("extra_args", {}),
                            "skills": item["skills"],
                            "tags": item.get("tags") or ["未分组"],
                        },
                    )
        except Exception as e:
            logger.error(f"批量保存资产失败: {e}")
            raise e

    def save_asset(
        self,
        remark,
        host,
        port,
        username,
        password,
        asset_type,
        agent_profile,
        extra_args,
        skills,
        tags=None,
        protocol=None,
    ) -> None:
        if tags is None:
            tags = ["未分组"]
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                self._upsert_asset(
                    cursor,
                    {
                        "remark": remark,
                        "host": host,
                        "port": port,
                        "username": username,
                        "password": password,
                        "asset_type": asset_type,
                        "protocol": protocol,
                        "agent_profile": agent_profile,
                        "extra_args": extra_args,
                        "skills": skills,
                        "tags": tags,
                    },
                )
        except Exception as e:
            logger.error(f"保存资产失败: {e}")
            raise

    def get_all_assets(self) -> list[dict]:
        try:
            with self._lock, self._connect() as conn:
                self._ensure_assets_protocol_column(conn)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT a.*, GROUP_CONCAT(t.name) as tags_concat
                    FROM assets a
                    LEFT JOIN asset_tags at ON a.id = at.asset_id
                    LEFT JOIN tags t ON at.tag_id = t.id
                    GROUP BY a.id
                    ORDER BY a.created_at DESC
                    """
                )
                return [self._asset_row(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"读取资产列表失败: {e}")
            return []

    def get_asset(self, asset_id: int) -> dict | None:
        try:
            with self._lock, self._connect() as conn:
                self._ensure_assets_protocol_column(conn)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT a.*, GROUP_CONCAT(t.name) as tags_concat
                    FROM assets a
                    LEFT JOIN asset_tags at ON a.id = at.asset_id
                    LEFT JOIN tags t ON at.tag_id = t.id
                    WHERE a.id = ?
                    GROUP BY a.id
                    """,
                    (asset_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._asset_row(row)
        except Exception as e:
            logger.error(f"读取资产失败: {e}")
            return None

    def update_asset(self, asset_id: int, item: dict) -> dict | None:
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                cursor.execute(
                    "SELECT password, extra_args_json FROM assets WHERE id = ?",
                    (asset_id,),
                )
                old = cursor.fetchone()
                if not old:
                    return None

                identity = resolve_asset_identity(
                    item.get("asset_type"),
                    item.get("protocol") or item.get("login_protocol"),
                    item.get("extra_args", {}),
                    item.get("host"),
                    item.get("port"),
                    item.get("remark"),
                )
                extra_args = self._encrypt_extra_args(
                    identity["extra_args"],
                    json.loads(old[1]) if old[1] else {},
                )
                password = self._encrypt_secret(item.get("password"), old[0])
                cursor.execute(
                    """
                    UPDATE assets
                    SET remark=?, host=?, port=?, username=?, password=?, asset_type=?, protocol=?, agent_profile=?, extra_args_json=?, skills_json=?
                    WHERE id=?
                    """,
                    (
                        item.get("remark", ""),
                        item.get("host", ""),
                        int(item.get("port") or 22),
                        item.get("username", ""),
                        password,
                        identity["asset_type"],
                        identity["protocol"],
                        item.get("agent_profile", "default"),
                        json.dumps(extra_args, ensure_ascii=False),
                        json.dumps(item.get("skills", []), ensure_ascii=False),
                        asset_id,
                    ),
                )
                self._replace_asset_tags(
                    cursor,
                    asset_id,
                    item.get("tags") or ["未分组"],
                )
            return self.get_asset(asset_id)
        except Exception as e:
            logger.error(f"更新资产失败: {e}")
            raise

    def delete_asset(self, asset_id: int) -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        except Exception as e:
            logger.error(f"删除资产失败: {e}")

    def _upsert_asset(self, cursor: sqlite3.Cursor, item: dict) -> None:
        host = item["host"]
        identity = resolve_asset_identity(
            item.get("asset_type"),
            item.get("protocol"),
            item.get("extra_args", {}),
            host,
            item.get("port"),
            item.get("remark"),
        )
        asset_type = identity["asset_type"]
        protocol = identity["protocol"]
        extra_args = identity["extra_args"]
        row = self._find_existing_asset(cursor, host, asset_type, protocol)

        if row:
            asset_id = row[0]
            old_password = row[1]
            old_extra_args = json.loads(row[2]) if row[2] else {}
            new_extra_args = self._encrypt_extra_args(extra_args, old_extra_args)
            new_password = self._encrypt_secret(item.get("password"), old_password)
            cursor.execute(
                """
                UPDATE assets
                SET remark=?, port=?, username=?, password=?, asset_type=?, protocol=?,
                    agent_profile=?, extra_args_json=?, skills_json=?
                WHERE id=?
                """,
                (
                    item["remark"],
                    item["port"],
                    item["username"],
                    new_password,
                    asset_type,
                    protocol,
                    item["agent_profile"],
                    json.dumps(new_extra_args, ensure_ascii=False),
                    json.dumps(item["skills"], ensure_ascii=False),
                    asset_id,
                ),
            )
        else:
            new_extra_args = self._encrypt_extra_args(extra_args)
            new_password = self._encrypt_secret(item.get("password"))
            cursor.execute(
                """
                INSERT INTO assets
                    (remark, host, port, username, password, asset_type, protocol,
                     agent_profile, extra_args_json, skills_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["remark"],
                    host,
                    item["port"],
                    item["username"],
                    new_password,
                    asset_type,
                    protocol,
                    item["agent_profile"],
                    json.dumps(new_extra_args, ensure_ascii=False),
                    json.dumps(item["skills"], ensure_ascii=False),
                ),
            )
            asset_id = cursor.lastrowid

        self._replace_asset_tags(cursor, asset_id, item.get("tags") or ["未分组"])

    def _find_existing_asset(
        self,
        cursor: sqlite3.Cursor,
        host: str,
        asset_type: str,
        protocol: str,
    ):
        cursor.execute(
            """
            SELECT id, password, extra_args_json, asset_type, protocol, remark, port
            FROM assets
            WHERE host = ?
            """,
            (host,),
        )
        for candidate in cursor.fetchall():
            old_args = json.loads(candidate[2]) if candidate[2] else {}
            old_identity = resolve_asset_identity(
                candidate[3],
                candidate[4],
                old_args,
                host,
                candidate[6],
                candidate[5],
            )
            if (
                old_identity["asset_type"] == asset_type
                and old_identity["protocol"] == protocol
            ):
                return candidate
        return None

    def _replace_asset_tags(
        self,
        cursor: sqlite3.Cursor,
        asset_id: int,
        tags: list[str],
    ) -> None:
        cursor.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))
        for tag in tags:
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            tag_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                (asset_id, tag_id),
            )

    def _asset_row(self, row) -> dict:
        asset = dict(row)
        raw_extra_args = (
            json.loads(asset["extra_args_json"]) if asset["extra_args_json"] else {}
        )
        asset["password"] = self._decrypt_secret(asset.get("password"))
        asset["extra_args"] = self._decrypt_extra_args(raw_extra_args)
        identity = resolve_asset_identity(
            asset.get("asset_type"),
            asset.get("protocol"),
            asset["extra_args"],
            asset.get("host"),
            asset.get("port"),
            asset.get("remark"),
        )
        asset["raw_asset_type"] = asset.get("asset_type")
        asset["asset_type"] = identity["asset_type"]
        asset["protocol"] = identity["protocol"]
        asset["extra_args"] = identity["extra_args"]
        asset["skills"] = (
            json.loads(asset["skills_json"]) if asset["skills_json"] else []
        )
        tags_str = asset.pop("tags_concat", None)
        asset["tags"] = tags_str.split(",") if tags_str else []
        if "group_name" in asset:
            asset.pop("group_name")
        return asset
