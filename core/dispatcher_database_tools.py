"""Database and datastore tool execution for the skill dispatcher."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.asset_protocols import SQL_PROTOCOLS
from core.safety_policy import check_readonly_block
from core.tool_policy_response import blocked_tool_response

logger = logging.getLogger(__name__)

DATABASE_TOOL_NAMES = {
    "db_execute_query",
    "redis_execute_command",
    "memcached_execute_command",
    "mongodb_find",
}


async def execute_database_tool(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    if tool_call_name == "db_execute_query":
        return await _execute_sql_query(tool_call_name, args, context)
    if tool_call_name == "redis_execute_command":
        return await _execute_redis_command(tool_call_name, args, context)
    if tool_call_name == "memcached_execute_command":
        return await _execute_memcached_command(tool_call_name, args, context)
    if tool_call_name == "mongodb_find":
        return await _execute_mongodb_find(args, context)
    return '{"error": "Unknown database tool"}'


async def _execute_sql_query(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.db_manager import db_executor, normalize_database_driver_key

    extra_args = context.get("extra_args") or {}
    db_type = (
        args.get("db_type")
        or extra_args.get("db_type")
        or extra_args.get("login_protocol")
        or context.get("protocol")
        or context.get("asset_type")
        or "mysql"
    )
    db_type = normalize_database_driver_key(str(db_type).lower())
    if db_type not in SQL_PROTOCOLS:
        return json.dumps(
            {
                "status": "ERROR",
                "error": f"当前数据源协议是 {db_type}，不能使用 db_execute_query；请使用对应的数据源工具。",
            },
            ensure_ascii=False,
        )

    host = context.get("host") or args.get("host")
    port = context.get("port") or args.get("port")
    user = context.get("username") or args.get("user")
    password = context.get("password")
    database = (
        extra_args.get("SID")
        or extra_args.get("service_name")
        or extra_args.get("database")
        or extra_args.get("db_name")
        or args.get("database")
        or ""
    )
    sql = args.get("sql")

    if args.get("password"):
        logger.warning("db_execute_query ignored model-supplied password and used managed session credentials.")
    if args.get("database") and database != args.get("database"):
        logger.warning("db_execute_query ignored model-supplied database and used managed session database.")

    if not all([db_type, host, port, user, password is not None, sql]):
        return json.dumps(
            {
                "status": "ERROR",
                "error": "数据库会话凭据不完整，请检查资产中心配置的 host/port/user/password/database。",
            },
            ensure_ascii=False,
        )

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    logger.info(
        "AI 调用原生数据库驱动 [%s] 查询: %s:%s/%s -> SQL: %s",
        db_type.upper(),
        host,
        port,
        database,
        sql,
    )
    return await asyncio.to_thread(
        db_executor.execute_query,
        db_type,
        host,
        port,
        user,
        password,
        database,
        sql,
        extra_args,
    )


async def _execute_redis_command(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.datastore_manager import redis_executor

    command = args.get("command", "")
    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        redis_executor.execute_command,
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        command=command,
        extra_args=context.get("extra_args") or {},
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_memcached_command(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.datastore_manager import memcached_executor

    command = args.get("command", "")
    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        memcached_executor.execute_command,
        host=context.get("host"),
        port=context.get("port") or 11211,
        command=command,
        extra_args=context.get("extra_args") or {},
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_mongodb_find(args: dict[str, Any], context: dict[str, Any]) -> str:
    from connections.datastore_manager import mongo_executor

    extra_args = context.get("extra_args") or {}
    database = args.get("database") or extra_args.get("database") or extra_args.get("db_name") or "admin"
    result = await asyncio.to_thread(
        mongo_executor.find,
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        database=database,
        collection=args.get("collection"),
        filter_doc=args.get("filter") or {},
        projection=args.get("projection"),
        limit=args.get("limit") or 100,
        extra_args=extra_args,
    )
    return json.dumps(result, ensure_ascii=False, default=str)
