import sqlite3
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from core.asset_profile_store import AssetProfileStore


class AssetProfileStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_asset_profile_store_{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "profiles.db"
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE asset_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    asset_key TEXT,
                    host TEXT,
                    asset_type TEXT,
                    protocol TEXT,
                    profile_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = AssetProfileStore(self._connect, Lock())

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

    def test_save_and_get_asset_profile_enriches_metadata(self):
        profile = {"summary": "ok"}
        self.store.save_asset_profile(
            "sid-1",
            "linux:10.0.0.1",
            "10.0.0.1",
            "linux",
            "ssh",
            profile,
        )

        loaded = self.store.get_asset_profile("sid-1")

        self.assertEqual(loaded["summary"], "ok")
        self.assertEqual(loaded["session_id"], "sid-1")
        self.assertEqual(loaded["asset_key"], "linux:10.0.0.1")
        self.assertEqual(loaded["host"], "10.0.0.1")
        self.assertEqual(loaded["asset_type"], "linux")
        self.assertEqual(loaded["protocol"], "ssh")
        self.assertIn("updated_at", loaded)

    def test_get_asset_profile_for_session_context_reuses_latest_same_asset(self):
        self.store.save_asset_profile(
            "sid-old",
            "linux:ssh:10.0.0.1:22",
            "10.0.0.1",
            "linux",
            "ssh",
            {"profile_prompt": "旧画像"},
        )
        self.store.save_asset_profile(
            "sid-latest",
            "linux:ssh:10.0.0.1:22",
            "10.0.0.1",
            "linux",
            "ssh",
            {"profile_prompt": "最新同资产画像"},
        )

        loaded = self.store.get_asset_profile_for_session_context(
            "sid-new",
            "linux:ssh:10.0.0.1:22",
            "10.0.0.1",
        )

        self.assertEqual(loaded["profile_prompt"], "最新同资产画像")
        self.assertEqual(loaded["session_id"], "sid-latest")


if __name__ == "__main__":
    unittest.main()
