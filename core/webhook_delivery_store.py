"""SQLite-backed webhook delivery audit storage."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Lock

logger = logging.getLogger(__name__)


class WebhookDeliveryStore:
    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        lock: Lock,
    ):
        self._connect = connect
        self._lock = lock

    def append_webhook_delivery(self, record: dict) -> dict:
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO webhook_deliveries
                        (session_id, webhook_host, channel, payload_type, title, status, http_status, response_preview, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("session_id") or "",
                        record.get("webhook_host") or "",
                        record.get("channel") or "",
                        record.get("payload_type") or "",
                        record.get("title") or "",
                        record.get("status") or "",
                        record.get("http_status"),
                        record.get("response_preview") or "",
                        record.get("error") or "",
                    ),
                )
                record["id"] = cursor.lastrowid
            return record
        except Exception as e:
            logger.error(f"记录 Webhook 发送历史失败: {e}")
            return record

    def list_webhook_deliveries(self, session_id: str, limit: int = 10) -> list[dict]:
        try:
            safe_limit = max(1, min(int(limit or 10), 50))
            with self._lock, self._connect() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT id, session_id, webhook_host, channel, payload_type, title, status,
                           http_status, response_preview, error, created_at
                    FROM webhook_deliveries
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (session_id, safe_limit),
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"读取 Webhook 发送历史失败: {e}")
            return []
