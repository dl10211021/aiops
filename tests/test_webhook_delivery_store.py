import sqlite3
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from core.webhook_delivery_store import WebhookDeliveryStore


class WebhookDeliveryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_webhook_delivery_store_{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "webhooks.db"
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE webhook_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    webhook_host TEXT,
                    channel TEXT,
                    payload_type TEXT,
                    title TEXT,
                    status TEXT,
                    http_status INTEGER,
                    response_preview TEXT,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = WebhookDeliveryStore(self._connect, Lock())

    def tearDown(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def test_append_and_list_webhook_deliveries_caps_limit(self):
        first = self.store.append_webhook_delivery(
            {
                "session_id": "sid-1",
                "webhook_host": "ops.local",
                "channel": "wechat",
                "payload_type": "card",
                "title": "告警",
                "status": "success",
                "http_status": 200,
                "response_preview": "ok",
            }
        )
        second = self.store.append_webhook_delivery({"session_id": "sid-1", "title": "恢复"})

        rows = self.store.list_webhook_deliveries("sid-1", limit=500)

        self.assertEqual(first["id"], 1)
        self.assertEqual(second["id"], 2)
        self.assertEqual([row["id"] for row in rows], [2, 1])
        self.assertEqual(rows[1]["webhook_host"], "ops.local")
        self.assertEqual(rows[1]["http_status"], 200)


if __name__ == "__main__":
    unittest.main()
