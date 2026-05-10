"""SQLite-backed short-term session message storage."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import datetime
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Lock

logger = logging.getLogger(__name__)

MAX_SESSION_CONTEXT_CHARS = 10_000_000


class SessionMessageStore:
    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        lock: Lock,
    ):
        self._connect = connect
        self._lock = lock

    def get_messages(
        self,
        session_id: str,
        for_ui: bool = False,
        limit: int | None = None,
    ) -> list[dict]:
        """获取 SQLite 中的短期记忆"""
        try:
            rows = self._fetch_message_rows(session_id, for_ui, limit)
            messages = message_rows_to_dicts(rows, for_ui=for_ui)
            valid_messages = sanitize_message_sequence(messages)
            return truncate_message_context(valid_messages)
        except Exception as e:
            logger.error(f"读取短期记忆库失败: {e}")
            return []

    def append_message(self, session_id: str, message_dict: dict) -> int | None:
        """存入 SQLite 作为短期记忆"""
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO memory (session_id, message_json) VALUES (?, ?)",
                    (session_id, json.dumps(message_dict, ensure_ascii=False)),
                )
                return int(cursor.lastrowid)
        except Exception as e:
            logger.error(f"保存记忆至 DB 失败: {e}")
            return None

    def update_message_exec_trace(
        self,
        session_id: str,
        message_id: int,
        exec_trace: list[dict],
    ) -> None:
        """Attach durable tool execution trace metadata to an assistant message."""
        try:
            with self._lock, self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT message_json FROM memory WHERE id = ? AND session_id = ?",
                    (message_id, session_id),
                )
                row = cursor.fetchone()
                if not row:
                    return
                message = json.loads(row[0])
                if message.get("role") != "assistant":
                    return
                message["exec_trace"] = exec_trace
                cursor.execute(
                    "UPDATE memory SET message_json = ? WHERE id = ? AND session_id = ?",
                    (json.dumps(message, ensure_ascii=False), message_id, session_id),
                )
        except Exception as e:
            logger.error(f"保存执行轨迹至 DB 失败: {e}")

    def update_message_content(
        self,
        session_id: str,
        message_id: int,
        content: str,
    ) -> dict:
        """修改单条用户可见消息内容。"""
        with self._lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_json FROM memory WHERE id = ? AND session_id = ?",
                (message_id, session_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("消息不存在或不属于当前会话")
            message = json.loads(row[0])
            if message.get("role") not in {"user", "assistant"}:
                raise ValueError("只能修改用户消息或 AI 输出")
            message["content"] = str(content or "")
            message["edited_at"] = time.time()
            if message.get("role") == "assistant":
                message.pop("tool_calls", None)
            cursor.execute(
                "UPDATE memory SET message_json = ? WHERE id = ? AND session_id = ?",
                (json.dumps(message, ensure_ascii=False), message_id, session_id),
            )
            conn.commit()
            message["_memory_id"] = message_id
            return message

    def update_message_feedback(
        self,
        session_id: str,
        message_id: int,
        rating: str,
        note: str | None = None,
    ) -> dict:
        """Record user feedback for an assistant answer and append feedback memory."""
        normalized_rating = str(rating or "").strip().lower()
        if normalized_rating not in {"up", "down"}:
            raise ValueError("反馈类型无效。")
        with self._lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_json FROM memory WHERE id = ? AND session_id = ?",
                (message_id, session_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("消息不存在或不属于当前会话")
            message = json.loads(row[0])
            if message.get("role") != "assistant":
                raise ValueError("只能反馈 AI 输出")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            feedback = {
                "rating": normalized_rating,
                "note": str(note or "").strip(),
                "created_at": now,
                "memory_policy": "promote" if normalized_rating == "up" else "do_not_promote_answer",
            }
            message["feedback"] = feedback
            cursor.execute(
                "UPDATE memory SET message_json = ? WHERE id = ? AND session_id = ?",
                (json.dumps(message, ensure_ascii=False), message_id, session_id),
            )
            label = "好评" if normalized_rating == "up" else "差评"
            policy = (
                "用户认为这条 AI 回答很好，可作为后续同类任务的表达和排查参考，但仍需基于实时工具结果验证。"
                if normalized_rating == "up"
                else "用户认为这条 AI 回答较差或错误，禁止把该回答当事实、建议或成功经验沉淀；后续遇到同类问题要主动规避。"
            )
            feedback_memory = {
                "role": "system",
                "content": "\n".join(
                    [
                        "【用户反馈记忆】",
                        f"反馈对象：消息 {message_id}",
                        f"反馈结果：{label}",
                        f"处理策略：{policy}",
                        f"用户备注：{feedback['note'] or '-'}",
                    ]
                ),
                "memory_type": "answer_feedback",
                "feedback_target_message_id": message_id,
                "feedback_rating": normalized_rating,
            }
            cursor.execute(
                "INSERT INTO memory (session_id, message_json) VALUES (?, ?)",
                (session_id, json.dumps(feedback_memory, ensure_ascii=False)),
            )
            conn.commit()
            message["_memory_id"] = message_id
            return message

    def delete_message(self, session_id: str, message_id: int) -> None:
        """删除单条用户可见消息。"""
        with self._lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_json FROM memory WHERE id = ? AND session_id = ?",
                (message_id, session_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("消息不存在或不属于当前会话")
            message = json.loads(row[0])
            if message.get("role") not in {"user", "assistant"}:
                raise ValueError("只能删除用户消息或 AI 输出")
            cursor.execute(
                "DELETE FROM memory WHERE id = ? AND session_id = ?",
                (message_id, session_id),
            )
            conn.commit()

    def clear_history(self, session_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM memory WHERE session_id = ?", (session_id,))
            conn.commit()

    def _fetch_message_rows(
        self,
        session_id: str,
        for_ui: bool,
        limit: int | None = None,
    ) -> list[tuple]:
        with self._lock, self._connect() as conn:
            cursor = conn.cursor()
            if for_ui:
                if limit and limit > 0:
                    cursor.execute(
                        """
                        SELECT id, message_json, timestamp
                        FROM (
                            SELECT id, message_json, timestamp
                            FROM memory
                            WHERE session_id = ?
                            ORDER BY id DESC
                            LIMIT ?
                        )
                        ORDER BY id ASC
                        """,
                        (session_id, limit),
                    )
                else:
                    cursor.execute(
                        "SELECT id, message_json, timestamp FROM memory WHERE session_id = ? ORDER BY id ASC",
                        (session_id,),
                    )
            else:
                cursor.execute(
                    "SELECT id, message_json FROM memory WHERE session_id = ? AND is_compressed = 0 ORDER BY id ASC",
                    (session_id,),
                )
            return cursor.fetchall()


def message_rows_to_dicts(rows: list[tuple], for_ui: bool = False) -> list[dict]:
    messages: list[dict] = []
    for row in rows:
        try:
            msg = json.loads(row[1])
            if isinstance(msg, dict) and "role" in msg:
                if for_ui and msg.get("memory_type") == "answer_feedback":
                    continue
                if for_ui:
                    msg["_memory_id"] = row[0]
                    if len(row) > 2:
                        msg["created_at"] = row[2]
                if not for_ui and is_protocol_retry_noise(msg):
                    continue
                if (
                    msg.get("role") == "user"
                    and "[System Auto Reply] Tools execution complete."
                    in str(msg.get("content"))
                ):
                    continue
                if msg.get("role") == "assistant" and "[System Notice:" in str(
                    msg.get("content")
                ):
                    continue
                messages.append(msg)
        except Exception:
            pass
    return messages


def is_protocol_retry_noise(msg: dict) -> bool:
    """Drop obsolete local-script retry loops from model context."""
    if msg.get("name") == "local_execute_script":
        return True
    content = str(msg.get("content") or "")
    if "禁止在 local_execute_script 中使用 Shell 控制符" in content:
        return True
    if "调整命令格式" in content and "WinRM" in content and "Shell 控制符" in content:
        return True
    if "run_winrm.py" in content or "local_execute_script" in content:
        return True
    if "本地脚本" in content and ("WinRM" in content or "Windows" in content):
        return True
    if "无法获取明文密码" in content or "常见弱口令" in content:
        return True
    return False


def sanitize_message_sequence(messages: list[dict]) -> list[dict]:
    """Build a tool-call-valid message sequence for OpenAI chat context."""
    valid_messages: list[dict] = []
    expected_tool_calls: set[str] = set()

    for msg in messages:
        role = msg.get("role")

        if role == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id in expected_tool_calls:
                expected_tool_calls.remove(tool_call_id)
                valid_messages.append(msg)
            continue

        if expected_tool_calls:
            _remove_pending_tool_calls(valid_messages)
            expected_tool_calls.clear()
            while valid_messages and valid_messages[-1].get("role") == "tool":
                valid_messages.pop()

        if role == "assistant":
            valid_messages.append(msg)
            if "tool_calls" in msg and msg["tool_calls"]:
                expected_tool_calls = {
                    tool_call["id"] for tool_call in msg["tool_calls"]
                }
        else:
            valid_messages.append(msg)

    if expected_tool_calls:
        _remove_pending_tool_calls(valid_messages)
        while valid_messages and valid_messages[-1].get("role") == "tool":
            valid_messages.pop()

    return valid_messages


def truncate_message_context(messages: list[dict]) -> list[dict]:
    truncated: list[dict] = []
    current_len = 0
    for msg in reversed(messages):
        msg_str = json.dumps(msg, ensure_ascii=False)
        if current_len + len(msg_str) > MAX_SESSION_CONTEXT_CHARS:
            break
        truncated.insert(0, msg)
        current_len += len(msg_str)

    while truncated:
        first_msg = truncated[0]
        if first_msg.get("role") == "tool":
            truncated.pop(0)
        elif first_msg.get("role") == "assistant" and "tool_calls" in first_msg:
            truncated.pop(0)
        elif first_msg.get("role") == "assistant" and not first_msg.get("content"):
            truncated.pop(0)
        elif first_msg.get("role") == "user":
            break
        else:
            break

    return truncated


def _remove_pending_tool_calls(messages: list[dict]) -> None:
    for i in range(len(messages) - 1, -1, -1):
        prev_msg = messages[i]
        if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
            prev_msg.pop("tool_calls", None)
            if not prev_msg.get("content"):
                prev_msg["content"] = "[Action aborted or incomplete]"
            break
