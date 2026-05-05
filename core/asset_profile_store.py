"""SQLite-backed asset profile memory storage."""

from __future__ import annotations

import datetime
import json
import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Lock

logger = logging.getLogger(__name__)


class AssetProfileStore:
    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        lock: Lock,
    ):
        self._connect = connect
        self._lock = lock

    def save_asset_profile(
        self,
        session_id: str,
        asset_key: str,
        host: str,
        asset_type: str,
        protocol: str,
        profile: dict,
    ) -> dict:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = json.dumps(profile, ensure_ascii=False)
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO asset_profiles
                        (session_id, asset_key, host, asset_type, protocol, profile_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        asset_key=excluded.asset_key,
                        host=excluded.host,
                        asset_type=excluded.asset_type,
                        protocol=excluded.protocol,
                        profile_json=excluded.profile_json,
                        updated_at=excluded.updated_at
                    """,
                    (session_id, asset_key, host, asset_type, protocol, payload, now, now),
                )
            return profile
        except Exception as e:
            logger.error(f"保存资产画像失败: {e}")
            raise

    def get_asset_profile(self, session_id: str) -> dict | None:
        try:
            with self._lock, self._connect() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """
                    SELECT session_id, asset_key, host, asset_type, protocol, profile_json, updated_at
                    FROM asset_profiles
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()
            if not row:
                return None
            profile = json.loads(row["profile_json"])
            if isinstance(profile, dict):
                profile.setdefault("session_id", row["session_id"])
                profile.setdefault("asset_key", row["asset_key"])
                profile.setdefault("host", row["host"])
                profile.setdefault("asset_type", row["asset_type"])
                profile.setdefault("protocol", row["protocol"])
                profile.setdefault("updated_at", row["updated_at"])
                return profile
        except Exception as e:
            logger.error(f"读取资产画像失败: {e}")
        return None

    def get_asset_profile_for_session_context(
        self,
        session_id: str,
        asset_key: str,
        host: str,
    ) -> dict | None:
        """Read the best profile for an independent session context."""
        session_id = str(session_id or "").strip()
        asset_key = str(asset_key or "").strip()
        host = str(host or "").strip()
        where_parts = []
        params: list[str] = []
        if session_id:
            where_parts.append("session_id = ?")
            params.append(session_id)
        if asset_key:
            where_parts.append("asset_key = ?")
            params.append(asset_key)
        if host:
            where_parts.append("host = ?")
            params.append(host)
        if not where_parts:
            return None
        try:
            with self._lock, self._connect() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    f"""
                    SELECT session_id, asset_key, host, asset_type, protocol, profile_json, updated_at
                    FROM asset_profiles
                    WHERE {' OR '.join(where_parts)}
                    ORDER BY
                        CASE
                            WHEN session_id = ? THEN 0
                            WHEN asset_key = ? THEN 1
                            WHEN host = ? THEN 2
                            ELSE 3
                        END,
                        updated_at DESC,
                        id DESC
                    LIMIT 1
                    """,
                    (*params, session_id, asset_key, host),
                ).fetchone()
            if not row:
                return None
            profile = json.loads(row["profile_json"])
            if isinstance(profile, dict):
                profile.setdefault("session_id", row["session_id"])
                profile.setdefault("asset_key", row["asset_key"])
                profile.setdefault("host", row["host"])
                profile.setdefault("asset_type", row["asset_type"])
                profile.setdefault("protocol", row["protocol"])
                profile.setdefault("updated_at", row["updated_at"])
                return profile
        except Exception as e:
            logger.error(f"读取同资产画像失败: {e}")
        return None
