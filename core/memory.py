import sqlite3
import threading
import json
import os
import logging
import datetime
import asyncio
import pyarrow as pa
import lancedb
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class MemoryDB:
    """基于 SQLite 的短期记忆 (STM) 和 LanceDB 的长期记忆 (LTM) 混合持久化模块"""

    def __init__(self):
        # 数据库存放在项目的根目录
        self._db_lock = threading.Lock()
        self.root_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(self.root_dir, "opscore.db")
        self.lancedb_path = os.path.join(self.root_dir, "opscore_lancedb")

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

        self.sensitive_keys = [
            "bearer_token",
            "kubeconfig",
            "api_token",
            "v3_auth_pass",
            "v3_priv_pass",
            "community_string",
            "enable_pass",
        ]

        self.init_db()

    def _get_embedding_model(self):
        try:
            from core.agent import EMBEDDING_MODEL

            return EMBEDDING_MODEL
        except ImportError:
            return "models/gemini-embedding-001"

    def _get_embedding_dim(self):
        try:
            from core.agent import EMBEDDING_DIM

            return EMBEDDING_DIM
        except ImportError:
            return 3072

    def init_db(self):
        try:
            # Init SQLite
            with sqlite3.connect(self.db_path) as conn:
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
            logger.info(f"SQLite 记忆库已就绪: {self.db_path}")

            # Init LanceDB
            self.ldb = lancedb.connect(self.lancedb_path)
            if "long_term_memory" not in self.ldb.table_names():
                self.ldb.create_table("long_term_memory", schema=self.ltm_schema)
            logger.info(f"LanceDB 长效记忆库已就绪: {self.lancedb_path}")

        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")

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
                    except Exception as e:
                        # might not be encrypted
                        pass
        return args_copy

    # -------- 资产持久化管理 --------
    def save_assets_batch(self, items: list[dict]):
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for item in items:
                    host = item["host"]
                    asset_type = item["asset_type"]
                    tags = item.get("tags") or ["未分组"]

                    cursor.execute(
                        "SELECT id, extra_args_json FROM assets WHERE host = ? AND asset_type = ?",
                        (host, asset_type),
                    )
                    row = cursor.fetchone()
                    if row:
                        asset_id = row[0]
                        old_extra_args = json.loads(row[1]) if row[1] else {}
                        new_extra_args = self._encrypt_extra_args(
                            item.get("extra_args", {}), old_extra_args
                        )
                        cursor.execute(
                            """
                            UPDATE assets SET remark=?, port=?, username=?, password=?, agent_profile=?, extra_args_json=?, skills_json=? WHERE id=?
                        """,
                            (
                                item["remark"],
                                item["port"],
                                item["username"],
                                item["password"],
                                item["agent_profile"],
                                json.dumps(new_extra_args, ensure_ascii=False),
                                json.dumps(item["skills"], ensure_ascii=False),
                                asset_id,
                            ),
                        )
                    else:
                        new_extra_args = self._encrypt_extra_args(
                            item.get("extra_args", {})
                        )
                        cursor.execute(
                            """
                            INSERT INTO assets (remark, host, port, username, password, asset_type, agent_profile, extra_args_json, skills_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                item["remark"],
                                host,
                                item["port"],
                                item["username"],
                                item["password"],
                                asset_type,
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
    ):
        if tags is None:
            tags = ["未分组"]
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, extra_args_json FROM assets WHERE host = ? AND asset_type = ?",
                    (host, asset_type),
                )
                row = cursor.fetchone()
                if row:
                    asset_id = row[0]
                    old_extra_args = json.loads(row[1]) if row[1] else {}
                    new_extra_args = self._encrypt_extra_args(
                        extra_args, old_extra_args
                    )
                    cursor.execute(
                        """
                        UPDATE assets SET remark=?, port=?, username=?, password=?, agent_profile=?, extra_args_json=?, skills_json=? WHERE id=?
                    """,
                        (
                            remark,
                            port,
                            username,
                            password,
                            asset_type,
                            agent_profile,
                            json.dumps(new_extra_args, ensure_ascii=False),
                            json.dumps(skills, ensure_ascii=False),
                            asset_id,
                        ),
                    )
                else:
                    new_extra_args = self._encrypt_extra_args(extra_args)
                    cursor.execute(
                        """
                        INSERT INTO assets (remark, host, port, username, password, asset_type, agent_profile, extra_args_json, skills_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            remark,
                            host,
                            port,
                            username,
                            password,
                            asset_type,
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

    def get_all_assets(self) -> list:
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
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
                    r["extra_args"] = self._decrypt_extra_args(raw_extra_args)
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

    def delete_asset(self, asset_id: int):
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        except Exception as e:
            logger.error(f"删除资产失败: {e}")

    # -------- 对话记忆管理 (STM + LTM) --------

    def get_messages(self, session_id: str, for_ui: bool = False) -> list:
        """获取 SQLite 中的短期记忆"""
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if for_ui:
                    cursor.execute(
                        "SELECT message_json FROM memory WHERE session_id = ? ORDER BY id ASC",
                        (session_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT message_json FROM memory WHERE session_id = ? AND is_compressed = 0 ORDER BY id ASC",
                        (session_id,),
                    )
                rows = cursor.fetchall()
                messages = []
                for row in rows:
                    try:
                        msg = json.loads(row[0])
                        if isinstance(msg, dict) and "role" in msg:
                            if (
                                msg.get("role") == "user"
                                and "[System Auto Reply] Tools execution complete."
                                in str(msg.get("content"))
                            ):
                                continue
                            if msg.get(
                                "role"
                            ) == "assistant" and "[System Notice:" in str(
                                msg.get("content")
                            ):
                                continue
                            messages.append(msg)
                    except:
                        pass

                # 重新构建一条严格符合 sequence 的记录，防止多并发导致 tool orphan 或未完成的 tool call
                valid_messages = []
                expected_tool_calls = set()

                for msg in messages:
                    role = msg.get("role")

                    if role == "tool":
                        tc_id = msg.get("tool_call_id")
                        if tc_id in expected_tool_calls:
                            expected_tool_calls.remove(tc_id)
                            valid_messages.append(msg)
                        else:
                            # 孤立的 tool message，直接丢弃
                            continue
                    else:
                        # 如果我们在期待 tool 的时候收到了其他消息（如 user），说明之前的 tool_calls 被打断了
                        if expected_tool_calls:
                            # 修正前一个 assistant 消息
                            for i in range(len(valid_messages) - 1, -1, -1):
                                prev_msg = valid_messages[i]
                                if (
                                    prev_msg.get("role") == "assistant"
                                    and "tool_calls" in prev_msg
                                ):
                                    prev_msg.pop("tool_calls", None)
                                    if not prev_msg.get("content"):
                                        prev_msg["content"] = (
                                            "[Action aborted or incomplete]"
                                        )
                                    break
                            expected_tool_calls.clear()

                            # 将已经被 append 的部分 tool 执行结果也回退掉
                            while (
                                valid_messages
                                and valid_messages[-1].get("role") == "tool"
                            ):
                                valid_messages.pop()

                        if role == "assistant":
                            valid_messages.append(msg)
                            if "tool_calls" in msg and msg["tool_calls"]:
                                expected_tool_calls = {
                                    tc["id"] for tc in msg["tool_calls"]
                                }
                        else:
                            valid_messages.append(msg)

                # 最后兜底：如果对话在 tool 执行完之前就意外中断了，同样清理掉
                if expected_tool_calls:
                    for i in range(len(valid_messages) - 1, -1, -1):
                        prev_msg = valid_messages[i]
                        if (
                            prev_msg.get("role") == "assistant"
                            and "tool_calls" in prev_msg
                        ):
                            prev_msg.pop("tool_calls", None)
                            if not prev_msg.get("content"):
                                prev_msg["content"] = "[Action aborted or incomplete]"
                            break
                    while valid_messages and valid_messages[-1].get("role") == "tool":
                        valid_messages.pop()

                messages = valid_messages

                # STM 取最近的上下文，保证不越界
                MAX_CHARS = 10_000_000
                truncated = []
                current_len = 0
                for msg in reversed(messages):
                    msg_str = json.dumps(msg, ensure_ascii=False)
                    if current_len + len(msg_str) > MAX_CHARS:
                        break
                    truncated.insert(0, msg)
                    current_len += len(msg_str)

                while truncated:
                    first_msg = truncated[0]
                    if first_msg.get("role") == "tool":
                        truncated.pop(0)
                    elif (
                        first_msg.get("role") == "assistant"
                        and "tool_calls" in first_msg
                    ):
                        truncated.pop(0)
                    elif first_msg.get("role") == "assistant" and not first_msg.get(
                        "content"
                    ):
                        truncated.pop(0)
                    elif first_msg.get("role") == "user":
                        break
                    else:
                        break

                return truncated
        except Exception as e:
            logger.error(f"读取短期记忆库失败: {e}")
            return []

    def append_message(self, session_id: str, message_dict: dict):
        """存入 SQLite 作为短期记忆"""
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO memory (session_id, message_json) VALUES (?, ?)",
                    (session_id, json.dumps(message_dict, ensure_ascii=False)),
                )
        except Exception as e:
            logger.error(f"保存记忆至 DB 失败: {e}")

    def clear_history(self, session_id: str):
        """清空指定会话的短期记忆"""
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memory WHERE session_id = ?", (session_id,))
                conn.commit()
            logger.info(f"已清空会话 {session_id} 的历史记忆")

            # 清理长期记忆向量碎片
            if "long_term_memory" in self.ldb.table_names():
                try:
                    tbl = self.ldb.open_table("long_term_memory")
                    tbl.cleanup_old_versions()
                    tbl.compact_files()
                    logger.info("LanceDB long_term_memory 碎片整理完成。")
                except Exception as e:
                    logger.warning(f"LanceDB 碎片整理失败: {e}")
        except Exception as e:
            logger.error(f"清空记忆失败: {e}")

    # -------- 长期记忆压缩与检索 (LanceDB) --------
    async def retrieve_ltm(
        self, session_id: str, query: str, client, limit: int = 3
    ) -> str:
        """根据用户查询检索相关的长期记忆节点"""
        try:
            table = self.ldb.open_table("long_term_memory")
            if table.count_rows() == 0:
                return ""

            # 获取用户 Query 的向量
            res = await client.embeddings.create(
                input=query, model=self._get_embedding_model()
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
        self, session_id: str, client, model_name: str = "gemini-2.5-flash"
    ):
        """将超出短期窗口的历史对话进行总结并存入 LanceDB，然后从 SQLite 释放"""
        try:
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
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

                resp = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )
                summary = resp.choices[0].message.content.strip()

                # 获取向量
                emb_res = await client.embeddings.create(
                    input=summary, model=self._get_embedding_model()
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
            with self._db_lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE memory SET is_compressed = 1 WHERE id IN ({','.join('?' * len(ids_to_delete))})",
                    ids_to_delete,
                )

        except Exception as e:
            logger.error(f"长期记忆压缩失败: {e}")


memory_db = MemoryDB()
