"""Adapters for non-SQL datastore assets."""

from __future__ import annotations

import logging
import shlex
import socket

logger = logging.getLogger(__name__)


class RedisExecutor:
    def execute_command(
        self,
        *,
        host: str,
        port: int,
        username: str = "",
        password: str | None = None,
        command: str,
        extra_args: dict | None = None,
    ) -> dict:
        extra_args = extra_args or {}
        try:
            import redis
        except ImportError:
            return {
                "success": False,
                "error": "缺少 redis 依赖，请先安装 requirements.txt 中的 redis 后再连接 Redis 资产。",
            }

        try:
            parts = shlex.split(command)
        except ValueError as e:
            return {"success": False, "error": f"Redis 命令解析失败: {e}"}
        if not parts:
            return {"success": False, "error": "Redis 命令不能为空"}

        try:
            client = redis.Redis(
                host=host,
                port=int(port),
                username=username or None,
                password=password or None,
                db=int(extra_args.get("database") or extra_args.get("db") or 0),
                ssl=bool(extra_args.get("use_ssl")),
                socket_connect_timeout=10,
                decode_responses=True,
            )
            result = client.execute_command(*parts)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error("Redis command failed: %s", e)
            return {"success": False, "error": str(e)}


class MongoExecutor:
    def find(
        self,
        *,
        host: str,
        port: int,
        username: str = "",
        password: str | None = None,
        database: str,
        collection: str,
        filter_doc: dict | None = None,
        projection: dict | None = None,
        limit: int = 100,
        extra_args: dict | None = None,
    ) -> dict:
        extra_args = extra_args or {}
        try:
            import pymongo
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pymongo 依赖，请先安装 requirements.txt 中的 pymongo 后再连接 MongoDB 资产。",
            }

        if not database or not collection:
            return {"success": False, "error": "MongoDB 查询需要 database 和 collection。"}

        try:
            client = pymongo.MongoClient(
                host=host,
                port=int(port),
                username=username or None,
                password=password or None,
                authSource=extra_args.get("auth_source") or database,
                tls=bool(extra_args.get("use_ssl")),
                serverSelectionTimeoutMS=8000,
            )
            client.admin.command("ping")
            cursor = client[database][collection].find(filter_doc or {}, projection).limit(
                max(1, min(int(limit or 100), 1000))
            )
            rows = list(cursor)
            for row in rows:
                if "_id" in row:
                    row["_id"] = str(row["_id"])
            return {"success": True, "count": len(rows), "data": rows}
        except Exception as e:
            logger.error("MongoDB query failed: %s", e)
            return {"success": False, "error": str(e)}


class MemcachedExecutor:
    READONLY_ROOTS = {"version", "stats", "get", "gets"}
    BLOCKED_ROOTS = {
        "add",
        "append",
        "cas",
        "decr",
        "delete",
        "flush_all",
        "gat",
        "gats",
        "incr",
        "prepend",
        "replace",
        "set",
        "touch",
    }

    def execute_command(
        self,
        *,
        host: str,
        port: int,
        command: str,
        extra_args: dict | None = None,
    ) -> dict:
        extra_args = extra_args or {}
        try:
            parts = shlex.split(str(command or "").strip())
        except ValueError as e:
            return {"success": False, "error": f"Memcached 命令解析失败: {e}"}
        if not parts:
            return {"success": False, "error": "Memcached 命令不能为空"}

        root = parts[0].lower()
        if root in self.BLOCKED_ROOTS or root not in self.READONLY_ROOTS:
            return {
                "success": False,
                "error": "Memcached 当前仅支持只读命令: version、stats、get、gets。",
            }
        if root in {"get", "gets"} and len(parts) < 2:
            return {"success": False, "error": "get/gets 需要至少一个 key。"}

        timeout = int(extra_args.get("timeout") or extra_args.get("socket_timeout") or 8)
        max_bytes = int(extra_args.get("max_response_bytes") or 1024 * 1024)
        wire_command = " ".join(parts) + "\r\n"

        try:
            with socket.create_connection((host, int(port or 11211)), timeout=timeout) as sock:
                sock.settimeout(timeout)
                sock.sendall(wire_command.encode("utf-8"))
                chunks: list[bytes] = []
                total = 0
                while total < max_bytes:
                    chunk = sock.recv(min(65536, max_bytes - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    joined = b"".join(chunks)
                    if root == "version" and joined.endswith(b"\r\n"):
                        break
                    if root in {"stats", "get", "gets"} and b"\r\nEND\r\n" in joined:
                        break

            text = b"".join(chunks).decode("utf-8", errors="replace")
            parsed = self._parse(root, text)
            return {
                "success": True,
                "command": " ".join(parts),
                "data": parsed,
                "output": text.strip(),
            }
        except Exception as e:
            logger.error("Memcached command failed: %s", e)
            return {"success": False, "error": str(e)}

    def _parse(self, root: str, text: str) -> object:
        lines = [line for line in text.replace("\r\n", "\n").split("\n") if line]
        if root == "version":
            first = lines[0] if lines else ""
            return {"version": first.replace("VERSION", "", 1).strip() if first.startswith("VERSION") else first}
        if root == "stats":
            stats: dict[str, str] = {}
            for line in lines:
                if line == "END":
                    continue
                parts = line.split(" ", 2)
                if len(parts) == 3 and parts[0] == "STAT":
                    stats[parts[1]] = parts[2]
            return stats
        values = []
        current: dict[str, object] | None = None
        for line in lines:
            if line == "END":
                break
            if line.startswith("VALUE "):
                parts = line.split()
                current = {
                    "key": parts[1] if len(parts) > 1 else "",
                    "flags": parts[2] if len(parts) > 2 else "",
                    "bytes": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None,
                    "cas": parts[4] if len(parts) > 4 else None,
                    "value": "",
                }
                values.append(current)
            elif current is not None:
                current["value"] = line
        return values


redis_executor = RedisExecutor()
mongo_executor = MongoExecutor()
memcached_executor = MemcachedExecutor()
