import sqlite3
import threading
import json
import os
import logging
import datetime
import asyncio
import sys
from contextlib import contextmanager
import pyarrow as pa
import lancedb
from cryptography.fernet import Fernet

from core.asset_profile_store import AssetProfileStore
from core.asset_protocols import normalize_protocol, resolve_asset_identity
from core.lancedb_utils import ensure_lancedb_table, lancedb_table_names
from core.session_message_store import SessionMessageStore, is_protocol_retry_noise
from core.slash_command_store import SlashCommandStore, slash_command_row
from core.webhook_delivery_store import WebhookDeliveryStore

logger = logging.getLogger(__name__)


DEFAULT_SENSITIVE_EXTRA_ARG_KEYS = [
    "access_key",
    "api_key",
    "api_token",
    "bearer_token",
    "client_secret",
    "community_string",
    "enable_pass",
    "enable_password",
    "kubeconfig",
    "secret_key",
    "v3_auth_pass",
    "v3_priv_pass",
    "vmware_session_id",
    "zstack_session_uuid",
]


class MemoryDB:
    """基于 SQLite 的短期记忆 (STM) 和 LanceDB 的长期记忆 (LTM) 混合持久化模块"""

    def __init__(self):
        # 数据库存放在项目的根目录
        self._db_lock = threading.Lock()
        self.root_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(self.root_dir, "opscore.db")
        self.lancedb_path = os.path.join(self.root_dir, "opscore_lancedb")
        self.ldb = None
        self.ltm_enabled = False

        # Init LanceDB Vector Table Schema
        self.ltm_schema = pa.schema(
            [
                pa.field("session_id", pa.string()),
                pa.field("timestamp", pa.string()),
                pa.field("summary", pa.string()),
                pa.field(
                    "vector", pa.list_(pa.float32(), self._get_embedding_dim())
                ),  # Configurable embedding dimension
            ]
        )

        # 初始化加解密
        try:
            self.key_path = os.path.join(self.root_dir, ".fernet.key")
            if os.path.exists(self.key_path):
                with open(self.key_path, "rb") as f:
                    self._key = f.read()
            else:
                self._key = Fernet.generate_key()
                with open(self.key_path, "wb") as f:
                    f.write(self._key)
            self._fernet = Fernet(self._key)
        except Exception as e:
            logger.warning(f"Failed to init Fernet encryption: {e}")
            self._fernet = None

        self.sensitive_keys = list(DEFAULT_SENSITIVE_EXTRA_ARG_KEYS)
        self._encrypted_prefix = "fernet:"
        self._session_message_store = SessionMessageStore(self._connect, self._db_lock)
        self._slash_command_store = SlashCommandStore(self._connect, self._db_lock)
        self._asset_profile_store = AssetProfileStore(self._connect, self._db_lock)
        self._webhook_delivery_store = WebhookDeliveryStore(self._connect, self._db_lock)

        self.init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _encrypt_secret(self, value, old_value=None):
        if value in (None, ""):
            return value
        if value == "********":
            return old_value or ""
        if not self._fernet or not isinstance(value, str):
            return value
        if value.startswith(self._encrypted_prefix):
            return value
        try:
            encrypted = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
            return f"{self._encrypted_prefix}{encrypted}"
        except Exception as e:
            logger.error(f"Secret encryption failed: {e}")
            return value

    def _decrypt_secret(self, value):
        if value in (None, ""):
            return value
        if not self._fernet or not isinstance(value, str):
            return value
        if not value.startswith(self._encrypted_prefix):
            return value
        try:
            token = value[len(self._encrypted_prefix) :]
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception:
            return value

    def _get_embedding_model(self):
        try:
            from core.embedding_config import EMBEDDING_MODEL

            return EMBEDDING_MODEL
        except ImportError:
            return ""

    def _get_embedding_dim(self):
        try:
            from core.embedding_config import EMBEDDING_DIM

            return EMBEDDING_DIM
        except ImportError:
            return 3072

    def init_db(self):
        try:
            # Init SQLite
            with self._connect() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                try:
                    conn.execute(
                        "ALTER TABLE memory ADD COLUMN is_compressed INTEGER DEFAULT 0"
                    )
                except:
                    pass
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        message_json TEXT,
                        is_compressed INTEGER DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # 资产连接表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS assets (
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
                self._ensure_assets_protocol_column(conn)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS asset_tags (
                        asset_id INTEGER,
                        tag_id INTEGER,
                        PRIMARY KEY (asset_id, tag_id),
                        FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS asset_profiles (
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
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS webhook_deliveries (
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
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS slash_commands (
                        id TEXT PRIMARY KEY,
                        label TEXT NOT NULL,
                        description TEXT,
                        prompt_template TEXT NOT NULL,
                        category TEXT DEFAULT '自定义',
                        scope_type TEXT DEFAULT 'global',
                        asset_type TEXT,
                        protocol TEXT,
                        host TEXT,
                        readonly INTEGER DEFAULT 1,
                        pinned INTEGER DEFAULT 0,
                        enabled INTEGER DEFAULT 1,
                        sort_order INTEGER DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            logger.info(f"SQLite 记忆库已就绪: {self.db_path}")

            self._init_lancedb()

        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")

    def _init_lancedb(self):
        if os.environ.get("OPSCORE_DISABLE_LTM", "").lower() in {"1", "true", "yes"}:
            logger.info("LanceDB 长效记忆已通过 OPSCORE_DISABLE_LTM 禁用。")
            return
        if "unittest" in sys.modules and os.environ.get("OPSCORE_ENABLE_LTM_IN_TESTS", "").lower() not in {"1", "true", "yes"}:
            logger.info("测试环境默认禁用 LanceDB 长效记忆。")
            return
        normalized_path = self.lancedb_path.replace("\\", "/").lower()
        if "/.codex/.sandbox/" in normalized_path:
            logger.info("当前运行在 Codex 文件系统沙箱内，LanceDB 长效记忆已禁用。")
            return

        try:
            os.makedirs(self.lancedb_path, exist_ok=True)
            probe_path = os.path.join(self.lancedb_path, ".write_probe")
            with open(probe_path, "w", encoding="utf-8") as f:
                f.write("ok")
            try:
                os.remove(probe_path)
            except OSError:
                pass
        except Exception as e:
            logger.warning(f"LanceDB 路径不可写，长效记忆已禁用: {e}")
            return

        try:
            self.ldb = lancedb.connect(self.lancedb_path)
            self._ensure_lancedb_table("long_term_memory", self.ltm_schema)
            self.ltm_enabled = True
            logger.info(f"LanceDB 长效记忆库已就绪: {self.lancedb_path}")
        except Exception as e:
            self.ldb = None
            self.ltm_enabled = False
            logger.warning(f"LanceDB 初始化失败，长效记忆已禁用: {e}")

    def _lancedb_table_names(self) -> list[str]:
        return lancedb_table_names(self.ldb)

    def _ensure_lancedb_table(self, table_name: str, schema) -> None:
        ensure_lancedb_table(self.ldb, table_name, schema)

    def _ensure_assets_protocol_column(self, conn):
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(assets)")]
            if "protocol" not in columns:
                conn.execute("ALTER TABLE assets ADD COLUMN protocol TEXT")
        except Exception as e:
            logger.warning(f"资产表 protocol 字段检查失败: {e}")

    def _encrypt_extra_args(self, new_args, old_args=None):
        if not new_args:
            return {}
        args_copy = dict(new_args)
        for k in self.sensitive_keys:
            if k in args_copy:
                v = args_copy[k]
                if v == "********":
                    if old_args and k in old_args:
                        args_copy[k] = old_args[k]
                    else:
                        args_copy.pop(k, None)
                elif v and self._fernet:
                    if isinstance(v, str):
                        try:
                            args_copy[k] = self._fernet.encrypt(
                                v.encode("utf-8")
                            ).decode("utf-8")
                        except Exception as e:
                            logger.error(f"Encryption failed for {k}: {e}")
        return args_copy

    def _decrypt_extra_args(self, args):
        if not args:
            return {}
        args_copy = dict(args)
        for k in self.sensitive_keys:
            if k in args_copy:
                v = args_copy[k]
                if v and self._fernet and isinstance(v, str):
                    try:
                        args_copy[k] = self._fernet.decrypt(v.encode("utf-8")).decode(
                            "utf-8"
                        )
                    except Exception:
                        # might not be encrypted
                        pass
        return args_copy

    # -------- 资产持久化管理 --------
    def save_assets_batch(self, items: list[dict]):
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                for item in items:
                    host = item["host"]
                    identity = resolve_asset_identity(
                        item.get("asset_type"),
                        item.get("protocol") or item.get("login_protocol"),
                        item.get("extra_args", {}),
                        host,
                        item.get("port"),
                        item.get("remark"),
                    )
                    asset_type = identity["asset_type"]
                    protocol = identity["protocol"]
                    extra_args = identity["extra_args"]
                    tags = item.get("tags") or ["未分组"]

                    cursor.execute(
                        "SELECT id, password, extra_args_json, asset_type, protocol, remark, port FROM assets WHERE host = ?",
                        (host,),
                    )
                    rows = cursor.fetchall()
                    row = None
                    for candidate in rows:
                        old_args = json.loads(candidate[2]) if candidate[2] else {}
                        old_identity = resolve_asset_identity(
                            candidate[3], candidate[4], old_args, host, candidate[6], candidate[5]
                        )
                        if old_identity["asset_type"] == asset_type and old_identity["protocol"] == protocol:
                            row = candidate
                            break
                    if row:
                        asset_id = row[0]
                        old_password = row[1]
                        old_extra_args = json.loads(row[2]) if row[2] else {}
                        new_extra_args = self._encrypt_extra_args(
                            extra_args, old_extra_args
                        )
                        new_password = self._encrypt_secret(
                            item.get("password"), old_password
                        )
                        cursor.execute(
                            """
                            UPDATE assets SET remark=?, port=?, username=?, password=?, asset_type=?, protocol=?, agent_profile=?, extra_args_json=?, skills_json=? WHERE id=?
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
                        new_extra_args = self._encrypt_extra_args(
                            extra_args
                        )
                        new_password = self._encrypt_secret(item.get("password"))
                        cursor.execute(
                            """
                            INSERT INTO assets (remark, host, port, username, password, asset_type, protocol, agent_profile, extra_args_json, skills_json)
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

                    cursor.execute(
                        "DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,)
                    )
                    for tag in tags:
                        cursor.execute(
                            "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,)
                        )
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                        tag_id = cursor.fetchone()[0]
                        cursor.execute(
                            "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                            (asset_id, tag_id),
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
    ):
        if tags is None:
            tags = ["未分组"]
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                identity = resolve_asset_identity(
                    asset_type, protocol, extra_args, host, port, remark
                )
                asset_type = identity["asset_type"]
                protocol = identity["protocol"]
                extra_args = identity["extra_args"]
                cursor.execute(
                    "SELECT id, password, extra_args_json, asset_type, protocol, remark, port FROM assets WHERE host = ?",
                    (host,),
                )
                rows = cursor.fetchall()
                row = None
                for candidate in rows:
                    old_args = json.loads(candidate[2]) if candidate[2] else {}
                    old_identity = resolve_asset_identity(
                        candidate[3], candidate[4], old_args, host, candidate[6], candidate[5]
                    )
                    if old_identity["asset_type"] == asset_type and old_identity["protocol"] == protocol:
                        row = candidate
                        break
                if row:
                    asset_id = row[0]
                    old_password = row[1]
                    old_extra_args = json.loads(row[2]) if row[2] else {}
                    new_extra_args = self._encrypt_extra_args(
                        extra_args, old_extra_args
                    )
                    new_password = self._encrypt_secret(password, old_password)
                    cursor.execute(
                        """
                        UPDATE assets SET remark=?, port=?, username=?, password=?, asset_type=?, protocol=?, agent_profile=?, extra_args_json=?, skills_json=? WHERE id=?
                    """,
                        (
                            remark,
                            port,
                            username,
                            new_password,
                            asset_type,
                            protocol,
                            agent_profile,
                            json.dumps(new_extra_args, ensure_ascii=False),
                            json.dumps(skills, ensure_ascii=False),
                            asset_id,
                        ),
                    )
                else:
                    new_extra_args = self._encrypt_extra_args(extra_args)
                    new_password = self._encrypt_secret(password)
                    cursor.execute(
                        """
                        INSERT INTO assets (remark, host, port, username, password, asset_type, protocol, agent_profile, extra_args_json, skills_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            remark,
                            host,
                            port,
                            username,
                            new_password,
                            asset_type,
                            protocol,
                            agent_profile,
                            json.dumps(new_extra_args, ensure_ascii=False),
                            json.dumps(skills, ensure_ascii=False),
                        ),
                    )
                    asset_id = cursor.lastrowid

                cursor.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))
                for tag in tags:
                    cursor.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,)
                    )
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                        (asset_id, tag_id),
                    )
        except Exception as e:
            logger.error(f"保存资产失败: {e}")
            raise

    def get_all_assets(self) -> list:
        try:
            with self._db_lock, self._connect() as conn:
                self._ensure_assets_protocol_column(conn)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, GROUP_CONCAT(t.name) as tags_concat
                    FROM assets a
                    LEFT JOIN asset_tags at ON a.id = at.asset_id
                    LEFT JOIN tags t ON at.tag_id = t.id
                    GROUP BY a.id
                    ORDER BY a.created_at DESC
                """)
                rows = cursor.fetchall()
                assets = []
                for row in rows:
                    r = dict(row)
                    raw_extra_args = (
                        json.loads(r["extra_args_json"]) if r["extra_args_json"] else {}
                    )
                    r["password"] = self._decrypt_secret(r.get("password"))
                    r["extra_args"] = self._decrypt_extra_args(raw_extra_args)
                    identity = resolve_asset_identity(
                        r.get("asset_type"),
                        r.get("protocol"),
                        r["extra_args"],
                        r.get("host"),
                        r.get("port"),
                        r.get("remark"),
                    )
                    r["raw_asset_type"] = r.get("asset_type")
                    r["asset_type"] = identity["asset_type"]
                    r["protocol"] = identity["protocol"]
                    r["extra_args"] = identity["extra_args"]
                    r["skills"] = (
                        json.loads(r["skills_json"]) if r["skills_json"] else []
                    )
                    tags_str = r.pop("tags_concat", None)
                    r["tags"] = tags_str.split(",") if tags_str else []
                    if "group_name" in r:
                        r.pop("group_name")
                    assets.append(r)
                return assets
        except Exception as e:
            logger.error(f"读取资产列表失败: {e}")
            return []

    def get_asset(self, asset_id: int) -> dict | None:
        try:
            with self._db_lock, self._connect() as conn:
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
                r = dict(row)
                raw_extra_args = json.loads(r["extra_args_json"]) if r["extra_args_json"] else {}
                r["password"] = self._decrypt_secret(r.get("password"))
                r["extra_args"] = self._decrypt_extra_args(raw_extra_args)
                identity = resolve_asset_identity(
                    r.get("asset_type"),
                    r.get("protocol"),
                    r["extra_args"],
                    r.get("host"),
                    r.get("port"),
                    r.get("remark"),
                )
                r["raw_asset_type"] = r.get("asset_type")
                r["asset_type"] = identity["asset_type"]
                r["protocol"] = identity["protocol"]
                r["extra_args"] = identity["extra_args"]
                r["skills"] = json.loads(r["skills_json"]) if r["skills_json"] else []
                tags_str = r.pop("tags_concat", None)
                r["tags"] = tags_str.split(",") if tags_str else []
                return r
        except Exception as e:
            logger.error(f"读取资产失败: {e}")
            return None

    def update_asset(self, asset_id: int, item: dict) -> dict | None:
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.cursor()
                self._ensure_assets_protocol_column(conn)
                cursor.execute("SELECT password, extra_args_json FROM assets WHERE id = ?", (asset_id,))
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

                cursor.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))
                for tag in item.get("tags") or ["未分组"]:
                    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
                        (asset_id, tag_id),
                    )
            return self.get_asset(asset_id)
        except Exception as e:
            logger.error(f"更新资产失败: {e}")
            raise

    def delete_asset(self, asset_id: int):
        try:
            with self._db_lock, self._connect() as conn:
                conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        except Exception as e:
            logger.error(f"删除资产失败: {e}")

    # -------- 对话记忆管理 (STM + LTM) --------

    def _is_protocol_retry_noise(self, msg: dict) -> bool:
        return is_protocol_retry_noise(msg)

    def get_messages(self, session_id: str, for_ui: bool = False) -> list:
        return self._session_message_store.get_messages(session_id, for_ui)

    def append_message(self, session_id: str, message_dict: dict):
        self._session_message_store.append_message(session_id, message_dict)

    def update_message_content(self, session_id: str, message_id: int, content: str) -> dict:
        return self._session_message_store.update_message_content(
            session_id,
            message_id,
            content,
        )

    def delete_message(self, session_id: str, message_id: int):
        self._session_message_store.delete_message(session_id, message_id)

    def clear_history(self, session_id: str):
        """清空指定会话的短期记忆"""
        try:
            self._session_message_store.clear_history(session_id)
            logger.info(f"已清空会话 {session_id} 的历史记忆")

            # 清理长期记忆向量碎片
            if self.ltm_enabled and self.ldb and "long_term_memory" in self._lancedb_table_names():
                try:
                    tbl = self.ldb.open_table("long_term_memory")
                    tbl.cleanup_old_versions()
                    tbl.compact_files()
                    logger.info("LanceDB long_term_memory 碎片整理完成。")
                except Exception as e:
                    logger.warning(f"LanceDB 碎片整理失败: {e}")
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")

    # -------- 快捷命令 --------
    def list_slash_commands(self) -> list[dict]:
        return self._slash_command_store.list_slash_commands()

    def save_slash_command(self, command: dict) -> dict:
        return self._slash_command_store.save_slash_command(command)

    def delete_slash_command(self, command_id: str) -> bool:
        return self._slash_command_store.delete_slash_command(command_id)

    @staticmethod
    def _slash_command_row(row) -> dict:
        return slash_command_row(row)

    # -------- 资产画像记忆 --------
    def save_asset_profile(
        self,
        session_id: str,
        asset_key: str,
        host: str,
        asset_type: str,
        protocol: str,
        profile: dict,
    ) -> dict:
        return self._asset_profile_store.save_asset_profile(
            session_id,
            asset_key,
            host,
            asset_type,
            protocol,
            profile,
        )

    def get_asset_profile(self, session_id: str) -> dict | None:
        return self._asset_profile_store.get_asset_profile(session_id)

    # -------- Webhook 发送审计 --------
    def append_webhook_delivery(self, record: dict) -> dict:
        return self._webhook_delivery_store.append_webhook_delivery(record)

    def list_webhook_deliveries(self, session_id: str, limit: int = 10) -> list[dict]:
        return self._webhook_delivery_store.list_webhook_deliveries(session_id, limit)

    # -------- 长期记忆压缩与检索 (LanceDB) --------
    async def retrieve_ltm(
        self, session_id: str, query: str, client, embedding_model: str | None = None, limit: int = 3
    ) -> str:
        """根据用户查询检索相关的长期记忆节点"""
        if not self.ltm_enabled or not self.ldb:
            return ""
        try:
            table = self.ldb.open_table("long_term_memory")
            if table.count_rows() == 0:
                return ""

            # 获取用户 Query 的向量
            res = await client.embeddings.create(
                input=query, model=embedding_model or self._get_embedding_model()
            )
            query_vector = res.data[0].embedding

            # 搜索 LanceDB (使用线程池防止阻塞 event_loop)
            safe_session_id = session_id.replace("'", "''")

            def _do_search():
                return (
                    table.search(query_vector)
                    .where(f"session_id = '{safe_session_id}'")
                    .limit(limit)
                    .to_list()
                )

            results = await asyncio.to_thread(_do_search)

            if not results:
                return ""

            context = "【长期记忆检索结果 (与当前请求相关的过往事实)】\n"
            for row in results:
                context += f"- {row['timestamp']}: {row['summary']}\n"
            return context
        except Exception as e:
            logger.error(f"长期记忆检索失败: {e}")
            return ""

    async def compress_and_store_ltm(
        self, session_id: str, client, embedding_model: str | None = None
    ):
        """将超出短期窗口的历史对话进行总结并存入 LanceDB，然后从 SQLite 释放"""
        if not self.ltm_enabled or not self.ldb:
            return
        try:
            with self._db_lock, self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, message_json FROM memory WHERE session_id = ? AND is_compressed = 0 ORDER BY id ASC",
                    (session_id,),
                )
                rows = cursor.fetchall()

            # 设定阈值：当短期记忆大于 40 条时，提取前 20 条进行压缩
            COMPRESS_THRESHOLD = 40
            EXTRACT_COUNT = 20

            if len(rows) < COMPRESS_THRESHOLD:
                return  # 还没达到压缩条件

            # 获取要压缩的候选消息
            candidate_rows = rows[:EXTRACT_COUNT]

            # 安全截断：找到最后一条干净的用户消息作为分割点，防止把未完成的 Tool 截断
            safe_split_idx = -1
            for i in range(len(candidate_rows) - 1, -1, -1):
                msg = json.loads(candidate_rows[i][1])
                if msg.get("role") == "user":
                    safe_split_idx = i
                    break

            if safe_split_idx <= 0:
                return  # 找不到安全的截断点

            compress_rows = candidate_rows[:safe_split_idx]
            if not compress_rows:
                return

            # 提取文本准备总结
            text_to_summarize = ""
            for r in compress_rows:
                msg = json.loads(r[1])
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    text_to_summarize += f"[{role}]: {content}\n"

            # 调用 LLM 总结
            if not text_to_summarize.strip():
                # 无实质内容，直接从 SQLite 删除
                ids_to_delete = [r[0] for r in compress_rows]
            else:
                prompt = f"以下是一段过往的对话日志。请提取其中的关键事实、配置信息、用户的偏好或系统状态，写成一段简洁客观的总结，便于未来作为长期记忆供 AI 检索。不需要任何寒暄，直接输出核心信息：\n\n{text_to_summarize}"

                # 默认使用当前配置的模型，避免写死某个云厂商模型。
                compress_model = os.environ.get("COMPRESS_MODEL") or embedding_model or self._get_embedding_model()
                resp = await client.chat.completions.create(
                    model=compress_model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )
                summary = resp.choices[0].message.content.strip()

                # 获取向量
                emb_res = await client.embeddings.create(
                    input=summary, model=embedding_model or self._get_embedding_model()
                )
                vector = emb_res.data[0].embedding

                # 存入 LanceDB (使用线程池)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                table = self.ldb.open_table("long_term_memory")

                def _do_add():
                    table.add(
                        [
                            {
                                "session_id": session_id,
                                "timestamp": timestamp,
                                "summary": summary,
                                "vector": vector,
                            }
                        ]
                    )

                await asyncio.to_thread(_do_add)

                ids_to_delete = [r[0] for r in compress_rows]
                logger.info(
                    f"成功将 {len(ids_to_delete)} 条消息压缩进长期记忆 LanceDB。"
                )

            # 标记短期记忆为已压缩
            with self._db_lock, self._connect() as conn:
                conn.execute(
                    f"UPDATE memory SET is_compressed = 1 WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                    ids_to_delete,
                )

        except Exception as e:
            logger.error(f"长期记忆压缩失败: {e}")


memory_db = MemoryDB()
