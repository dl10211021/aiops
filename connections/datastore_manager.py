"""Adapters for non-SQL datastore assets."""

from __future__ import annotations

import logging
import shlex

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


redis_executor = RedisExecutor()
mongo_executor = MongoExecutor()
