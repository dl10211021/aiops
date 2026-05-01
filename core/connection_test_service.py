from __future__ import annotations

import asyncio
import json
import os
import subprocess
from typing import Any

from core.asset_protocols import API_PROTOCOLS, SQL_PROTOCOLS, resolve_asset_identity
from core.connection_errors import classify_connection_error
from core.connection_request_service import normalize_private_key_path


def connection_error_result(raw_error: Any, protocol: str = "", context: str = "") -> dict[str, Any]:
    error = classify_connection_error(raw_error, protocol, context)
    return {"status": "error", "message": error["message"], "data": {"error": error}}


async def run_connection_test(req: Any, restored_password: str | None) -> dict[str, Any]:
    if req.target_scope == "global":
        return {
            "status": "success",
            "message": "[OK] 全局总控会话无需连接单台资产，可直接创建。",
        }

    identity = resolve_asset_identity(
        req.asset_type,
        req.protocol,
        req.extra_args,
        req.host,
        req.port,
        req.remark,
    )
    login_protocol = identity["protocol"]

    if login_protocol == "ssh":
        return await _test_ssh(req, restored_password)
    if login_protocol == "winrm":
        return await _test_winrm(req, restored_password)

    requested_db_type = req.extra_args.get("db_type") if req.extra_args else None
    if login_protocol in SQL_PROTOCOLS or requested_db_type in SQL_PROTOCOLS:
        return await _test_sql_database(req, restored_password, login_protocol, requested_db_type)
    if login_protocol == "redis" or requested_db_type == "redis":
        return await _test_redis(req, restored_password)
    if login_protocol == "memcached" or requested_db_type == "memcached":
        return await _test_memcached(req)
    if login_protocol == "mongodb" or requested_db_type == "mongodb":
        return await _test_mongodb(req, restored_password)
    if login_protocol in API_PROTOCOLS or login_protocol == "snmp":
        return await _test_api_or_snmp_port(req, login_protocol)
    return await _test_virtual_ping(req)


async def _test_ssh(req: Any, restored_password: str | None) -> dict[str, Any]:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        await asyncio.to_thread(
            client.connect,
            hostname=req.host,
            port=req.port,
            username=req.username,
            password=restored_password,
            key_filename=normalize_private_key_path(req.private_key_path),
            timeout=5,
        )
        client.close()
        return {
            "status": "success",
            "message": "[OK] SSH Connection Successful! Credentials are valid.",
        }
    except Exception as exc:
        return connection_error_result(exc, "ssh")


async def _test_winrm(req: Any, restored_password: str | None) -> dict[str, Any]:
    from connections.winrm_manager import winrm_executor

    result = await asyncio.to_thread(
        winrm_executor.execute_command,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        command="$PSVersionTable.PSVersion.ToString()",
        extra_args=req.extra_args,
    )
    if result.get("success"):
        return {
            "status": "success",
            "message": "[OK] WinRM Connection Successful! Credentials are valid.",
        }
    return connection_error_result(
        result.get("error") or result.get("output"),
        "winrm",
        str(result.get("error_type") or ""),
    )


async def _test_sql_database(
    req: Any,
    restored_password: str | None,
    login_protocol: str,
    requested_db_type: str | None,
) -> dict[str, Any]:
    from connections.db_manager import db_executor, get_database_operation_profile

    db_type = req.extra_args.get("db_type") or login_protocol or "mysql"
    database = (
        req.extra_args.get("SID")
        or req.extra_args.get("service_name")
        or req.extra_args.get("database")
        or req.extra_args.get("db_name")
        or ""
    )
    sql = get_database_operation_profile(db_type).get("test_statement") or (
        "SELECT 1 FROM DUAL" if db_type == "oracle" else "SELECT 1"
    )

    result_text = await asyncio.to_thread(
        db_executor.execute_query,
        db_type,
        req.host,
        req.port,
        req.username,
        restored_password,
        database,
        sql,
        req.extra_args,
    )
    result = json.loads(result_text)
    if result.get("success"):
        return {
            "status": "success",
            "message": f"[OK] Database ({db_type.upper()}) Connection Successful!",
        }
    return connection_error_result(result.get("error"), db_type or requested_db_type or "")


async def _test_redis(req: Any, restored_password: str | None) -> dict[str, Any]:
    from connections.datastore_manager import redis_executor

    result = await asyncio.to_thread(
        redis_executor.execute_command,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        command="PING",
        extra_args=req.extra_args,
    )
    if result.get("success"):
        return {"status": "success", "message": "[OK] Redis Connection Successful!"}
    return connection_error_result(result.get("error"), "redis")


async def _test_memcached(req: Any) -> dict[str, Any]:
    from connections.datastore_manager import memcached_executor

    result = await asyncio.to_thread(
        memcached_executor.execute_command,
        host=req.host,
        port=req.port,
        command="version",
        extra_args=req.extra_args,
    )
    if result.get("success"):
        return {"status": "success", "message": "[OK] Memcached Connection Successful!"}
    return connection_error_result(result.get("error"), "memcached")


async def _test_mongodb(req: Any, restored_password: str | None) -> dict[str, Any]:
    from connections.datastore_manager import mongo_executor

    database = req.extra_args.get("database") or req.extra_args.get("db_name") or "admin"
    result = await asyncio.to_thread(
        mongo_executor.find,
        host=req.host,
        port=req.port,
        username=req.username,
        password=restored_password,
        database=database,
        collection=str(req.extra_args.get("test_collection") or "system.version"),
        filter_doc={},
        limit=1,
        extra_args=req.extra_args,
    )
    if result.get("success"):
        return {"status": "success", "message": "[OK] MongoDB Connection Successful!"}
    return connection_error_result(result.get("error"), "mongodb")


async def _test_api_or_snmp_port(req: Any, login_protocol: str) -> dict[str, Any]:
    import socket
    from urllib.parse import urlparse

    from connections.http_api_manager import build_base_url

    try:
        if login_protocol in API_PROTOCOLS:
            parsed = urlparse(build_base_url(req.host, req.port, req.extra_args))
            host = parsed.hostname or req.host
            port = parsed.port or req.port
        else:
            host = req.host
            port = req.port
        with socket.create_connection((host, port), timeout=3):
            pass
        return {
            "status": "success",
            "message": f"[OK] Port {port} is reachable. (Auth testing deferred to execution agent)",
        }
    except Exception as exc:
        return connection_error_result(exc, login_protocol, "tcp connect")


async def _test_virtual_ping(req: Any) -> dict[str, Any]:
    try:
        command = (
            ["ping", "-n", "1", "-w", "1000", req.host]
            if os.name == "nt"
            else ["ping", "-c", "1", "-W", "1", req.host]
        )
        result = await asyncio.to_thread(subprocess.run, command, capture_output=True)
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "[OK] ICMP Ping Successful! Target is reachable.",
            }
        return {
            "status": "success",
            "message": "[WARN] Ping failed (timeout or blocked). Virtual credentials saved.",
        }
    except Exception:
        return {"status": "success", "message": "[OK] Virtual credentials saved."}
