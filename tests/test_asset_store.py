import shutil
import sqlite3
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from core.asset_store import AssetStore


class AssetStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp_path = Path.cwd() / "tests" / f"tmp_asset_store_{uuid.uuid4().hex}"
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "assets.db"
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remark TEXT,
                    host TEXT,
                    port INTEGER,
                    username TEXT,
                    password TEXT,
                    asset_type TEXT,
                    agent_profile TEXT,
                    extra_args_json TEXT,
                    skills_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE asset_tags (
                    asset_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (asset_id, tag_id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self.store = AssetStore(
            self._connect,
            Lock(),
            self._ensure_assets_protocol_column,
            self._encrypt_secret,
            self._decrypt_secret,
            self._encrypt_extra_args,
            self._decrypt_extra_args,
        )

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

    def _ensure_assets_protocol_column(self, conn):
        columns = [row[1] for row in conn.execute("PRAGMA table_info(assets)")]
        if "protocol" not in columns:
            conn.execute("ALTER TABLE assets ADD COLUMN protocol TEXT")

    def _encrypt_secret(self, value, old_value=None):
        if value == "********":
            return old_value or ""
        if value in (None, ""):
            return value
        return f"enc:{value}"

    def _decrypt_secret(self, value):
        if isinstance(value, str) and value.startswith("enc:"):
            return value[4:]
        return value

    def _encrypt_extra_args(self, new_args, old_args=None):
        result = dict(new_args or {})
        for key in ("access_key", "secret_key"):
            if result.get(key) == "********":
                if old_args and key in old_args:
                    result[key] = old_args[key]
                else:
                    result.pop(key, None)
            elif result.get(key):
                result[key] = f"enc:{result[key]}"
        return result

    def _decrypt_extra_args(self, args):
        result = dict(args or {})
        for key, value in list(result.items()):
            if isinstance(value, str) and value.startswith("enc:"):
                result[key] = value[4:]
        return result

    def test_save_and_get_asset_normalizes_protocol_and_tags(self):
        self.store.save_asset(
            remark="prod-linux",
            host="10.0.0.1",
            port=22,
            username="root",
            password="secret",
            asset_type="linux",
            agent_profile="default",
            extra_args={},
            skills=["linux"],
            tags=["prod"],
        )

        asset = self.store.get_all_assets()[0]

        self.assertEqual(asset["password"], "secret")
        self.assertEqual(asset["asset_type"], "linux")
        self.assertEqual(asset["protocol"], "ssh")
        self.assertEqual(asset["skills"], ["linux"])
        self.assertEqual(asset["tags"], ["prod"])

    def test_update_asset_preserves_masked_secret_values(self):
        self.store.save_asset(
            remark="prod-s3",
            host="s3.internal",
            port=443,
            username="",
            password="secret-v1",
            asset_type="s3",
            protocol="s3",
            agent_profile="default",
            extra_args={
                "category": "storage",
                "sub_type": "s3",
                "access_key": "ak-v1",
                "secret_key": "sk-v1",
                "bucket": "logs",
            },
            skills=["storage"],
            tags=["old"],
        )
        asset_id = self.store.get_all_assets()[0]["id"]

        updated = self.store.update_asset(
            asset_id,
            {
                "remark": "prod-s3-renamed",
                "host": "s3.internal",
                "port": 443,
                "username": "",
                "password": "********",
                "asset_type": "s3",
                "protocol": "s3",
                "agent_profile": "default",
                "extra_args": {
                    "category": "storage",
                    "sub_type": "s3",
                    "access_key": "********",
                    "secret_key": "********",
                    "bucket": "ops",
                },
                "skills": ["storage"],
                "tags": ["new"],
            },
        )

        self.assertEqual(updated["remark"], "prod-s3-renamed")
        self.assertEqual(updated["password"], "secret-v1")
        self.assertEqual(updated["extra_args"]["access_key"], "ak-v1")
        self.assertEqual(updated["extra_args"]["secret_key"], "sk-v1")
        self.assertEqual(updated["extra_args"]["bucket"], "ops")
        self.assertEqual(updated["tags"], ["new"])

    def test_save_assets_batch_updates_existing_host_protocol_pair(self):
        self.store.save_assets_batch(
            [
                {
                    "remark": "old",
                    "host": "10.0.0.2",
                    "port": 22,
                    "username": "root",
                    "password": "old",
                    "asset_type": "linux",
                    "agent_profile": "default",
                    "extra_args": {},
                    "skills": ["linux"],
                    "tags": ["old"],
                },
                {
                    "remark": "new",
                    "host": "10.0.0.2",
                    "port": 2222,
                    "username": "admin",
                    "password": "new",
                    "asset_type": "linux",
                    "agent_profile": "dba",
                    "extra_args": {},
                    "skills": ["ops"],
                    "tags": ["new"],
                },
            ]
        )

        assets = self.store.get_all_assets()

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["remark"], "new")
        self.assertEqual(assets[0]["port"], 2222)
        self.assertEqual(assets[0]["password"], "new")
        self.assertEqual(assets[0]["tags"], ["new"])

    def test_delete_asset_removes_inventory_row(self):
        self.store.save_asset(
            remark="tmp",
            host="10.0.0.3",
            port=22,
            username="root",
            password="secret",
            asset_type="linux",
            agent_profile="default",
            extra_args={},
            skills=[],
        )
        asset_id = self.store.get_all_assets()[0]["id"]

        self.store.delete_asset(asset_id)

        self.assertEqual(self.store.get_asset(asset_id), None)
        self.assertEqual(self.store.get_all_assets(), [])


if __name__ == "__main__":
    unittest.main()
