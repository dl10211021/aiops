import os
import shutil
import sqlite3
import unittest
import uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
from cryptography.fernet import Fernet

from core.memory import MemoryDB


def make_memory_db() -> MemoryDB:
    tmpdir = str(Path.cwd() / "tests" / f"tmp_memory_{uuid.uuid4().hex}")
    os.makedirs(tmpdir, exist_ok=True)
    db = MemoryDB.__new__(MemoryDB)
    db._db_lock = __import__("threading").Lock()
    db.root_dir = tmpdir
    db.db_path = os.path.join(tmpdir, "opscore.db")
    db.lancedb_path = os.path.join(tmpdir, "opscore_lancedb")
    db.key_path = os.path.join(tmpdir, "fernet.key")
    db._key = Fernet.generate_key()
    db._fernet = Fernet(db._key)
    db._encrypted_prefix = "fernet:"
    db.sensitive_keys = [
        "bearer_token",
        "kubeconfig",
        "api_token",
        "v3_auth_pass",
        "v3_priv_pass",
        "community_string",
        "enable_pass",
    ]
    db.ltm_schema = pa.schema(
        [
            pa.field("session_id", pa.string()),
            pa.field("timestamp", pa.string()),
            pa.field("summary", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 3072)),
        ]
    )
    with closing(sqlite3.connect(db.db_path)) as conn:
        conn.execute("""
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
        """)
        conn.commit()
        conn.execute("""
            CREATE TABLE tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE asset_tags (
                asset_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (asset_id, tag_id)
            )
        """)
    return db


class TestMemorySecurity(unittest.TestCase):
    def tearDown(self):
        for p in (Path.cwd() / "tests").glob("tmp_memory_*"):
            shutil.rmtree(p, ignore_errors=True)

    def test_asset_password_is_encrypted_at_rest_and_decrypted_for_runtime(self):
        db = make_memory_db()

        db.save_asset(
            remark="prod",
            host="10.0.0.1",
            port=22,
            username="root",
            password="plain-secret",
            asset_type="ssh",
            agent_profile="default",
            extra_args={},
            skills=[],
            tags=["prod"],
        )

        with closing(sqlite3.connect(db.db_path)) as conn:
            raw_password = conn.execute(
                "SELECT password FROM assets WHERE host = ?", ("10.0.0.1",)
            ).fetchone()[0]

        self.assertNotEqual(raw_password, "plain-secret")
        self.assertEqual(db.get_all_assets()[0]["password"], "plain-secret")

    def test_existing_asset_update_succeeds_and_replaces_password(self):
        db = make_memory_db()

        db.save_asset(
            remark="old",
            host="10.0.0.2",
            port=22,
            username="root",
            password="old-secret",
            asset_type="ssh",
            agent_profile="default",
            extra_args={},
            skills=[],
            tags=["old"],
        )
        db.save_asset(
            remark="new",
            host="10.0.0.2",
            port=2222,
            username="admin",
            password="new-secret",
            asset_type="ssh",
            agent_profile="dba",
            extra_args={},
            skills=["linux"],
            tags=["new"],
        )

        assets = db.get_all_assets()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["remark"], "new")
        self.assertEqual(assets[0]["port"], 2222)
        self.assertEqual(assets[0]["username"], "admin")
        self.assertEqual(assets[0]["password"], "new-secret")
        self.assertEqual(assets[0]["skills"], ["linux"])
        self.assertEqual(assets[0]["tags"], ["new"])

    def test_protocol_retry_noise_is_filtered_from_model_context_only(self):
        db = MemoryDB.__new__(MemoryDB)

        assistant_noise = {
            "role": "assistant",
            "content": "收到，我将调整命令格式，避免使用 Shell 控制符，直接通过 WinRM 执行 PowerShell 脚本来获取系统信息。",
        }
        tool_noise = {
            "role": "tool",
            "name": "local_execute_script",
            "content": '{"status": "BLOCKED", "reason": "禁止在 local_execute_script 中使用 Shell 控制符或重定向"}',
        }
        normal = {"role": "assistant", "content": "正常巡检结果"}

        self.assertTrue(db._is_protocol_retry_noise(assistant_noise))
        self.assertTrue(db._is_protocol_retry_noise(tool_noise))
        self.assertTrue(db._is_protocol_retry_noise({
            "role": "assistant",
            "content": "我将通过本地脚本 run_winrm.py 尝试 Windows 密码试错。",
        }))
        self.assertTrue(db._is_protocol_retry_noise({
            "role": "assistant",
            "content": "由于我无法获取明文密码，我将尝试常见弱口令。",
        }))
        self.assertFalse(db._is_protocol_retry_noise(normal))

    def test_lancedb_existing_table_does_not_disable_ltm(self):
        db = make_memory_db()
        db.ldb = None
        db.ltm_enabled = False

        class FakeLanceDB:
            def list_tables(self):
                return []

            def create_table(self, name, schema):
                raise RuntimeError(f"Table '{name}' already exists")

            def open_table(self, name):
                return {"name": name}

        with (
            patch.dict(os.environ, {"OPSCORE_ENABLE_LTM_IN_TESTS": "1"}),
            patch("core.memory.lancedb.connect", return_value=FakeLanceDB()),
        ):
            db._init_lancedb()

        self.assertTrue(db.ltm_enabled)
        self.assertIsNotNone(db.ldb)


if __name__ == "__main__":
    unittest.main()
