"""Execute read-only inspection template steps."""

from __future__ import annotations

import asyncio
import json
from typing import Any


SSH_TEMPLATE_TOOLS = {
    "linux_execute_command",
    "container_execute_command",
    "middleware_execute_command",
    "storage_execute_command",
}

HTTP_TEMPLATE_TOOLS = {
    "http_api_request",
    "database_api_request",
    "bigdata_api_request",
    "middleware_api_request",
    "discovery_api_request",
    "container_api_request",
    "network_api_request",
    "security_api_request",
    "cicd_api_request",
    "ai_platform_api_request",
    "oob_api_request",
    "k8s_api_request",
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "service_probe_request",
}

OBJECT_STORAGE_ASSET_TYPES = {"s3", "minio", "oss", "cos", "obs", "object_storage"}


async def run_inspection_template(
    session_id: str,
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    template: dict[str, Any],
    ssh_client: Any,
) -> dict[str, Any]:
    checks = []
    extra_args = info.get("extra_args") or {}

    for step in template.get("steps", []):
        result = await execute_template_step(session_id, info, asset_type, protocol, step, extra_args, ssh_client)
        command = step.get("command") or step.get("sql") or step.get("path") or step.get("oid") or ""
        success = bool(result.get("success")) and not result.get("has_error")
        output = result.get("output") or result.get("error") or json.dumps(result, ensure_ascii=False, default=str)
        checks.append(
            {
                "name": step.get("name"),
                "title": step.get("title") or step.get("name"),
                "status": "success" if success else "error",
                "command": command,
                "output": output,
                "exit_status": result.get("exit_status") if "exit_status" in result else (0 if success else None),
            }
        )

    failed = [check for check in checks if check["status"] != "success"]
    return {
        "status": "success" if not failed else "warning",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "template",
        "template_id": template.get("id"),
        "summary": f"按模板 {template.get('name') or template.get('id')} 完成 {len(checks)} 项只读巡检，异常 {len(failed)} 项。",
        "checks": checks,
    }


async def execute_template_step(
    session_id: str,
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    step: dict[str, Any],
    extra_args: dict[str, Any],
    ssh_client: Any,
) -> dict[str, Any]:
    tool = step.get("tool")
    if tool in SSH_TEMPLATE_TOOLS:
        return await asyncio.to_thread(
            ssh_client.execute_command,
            session_id,
            step.get("command"),
            step.get("timeout") or 15,
        )
    if tool == "network_cli_execute_command":
        return await asyncio.to_thread(
            ssh_client.execute_network_cli_command,
            session_id,
            step.get("command"),
            step.get("timeout") or 15,
        )
    if tool == "winrm_execute_command":
        return await _execute_winrm_step(info, step, extra_args)
    if tool == "db_execute_query":
        return await _execute_db_step(info, protocol, step, extra_args)
    if tool == "redis_execute_command":
        return await _execute_redis_step(info, step, extra_args)
    if tool == "memcached_execute_command":
        return await _execute_memcached_step(info, step, extra_args)
    if tool == "mongodb_find":
        return await _execute_mongodb_step(info, step, extra_args)
    if tool in HTTP_TEMPLATE_TOOLS:
        return await _execute_http_style_step(info, asset_type, protocol, step, extra_args)
    if tool == "snmp_get":
        return await _execute_snmp_step(info, step, extra_args)
    return {"success": False, "error": f"不支持的巡检工具: {tool}"}


async def _execute_winrm_step(info: dict[str, Any], step: dict[str, Any], extra_args: dict[str, Any]) -> dict[str, Any]:
    from connections.winrm_manager import winrm_executor

    return await asyncio.to_thread(
        winrm_executor.execute_command,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username"),
        password=info.get("password"),
        command=step.get("command"),
        extra_args=extra_args,
    )


async def _execute_db_step(
    info: dict[str, Any],
    protocol: str,
    step: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.db_manager import db_executor

    database = (
        extra_args.get("SID")
        or extra_args.get("service_name")
        or extra_args.get("database")
        or extra_args.get("db_name")
        or ""
    )
    result_str = await asyncio.to_thread(
        db_executor.execute_query,
        protocol,
        info.get("host"),
        info.get("port"),
        info.get("username"),
        info.get("password"),
        database,
        step.get("sql") or step.get("command"),
        extra_args,
    )
    return {"success": True, "output": result_str, "exit_status": 0}


async def _execute_redis_step(info: dict[str, Any], step: dict[str, Any], extra_args: dict[str, Any]) -> dict[str, Any]:
    from connections.datastore_manager import redis_executor

    return await asyncio.to_thread(
        redis_executor.execute_command,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        command=step.get("command"),
        extra_args=extra_args,
    )


async def _execute_memcached_step(info: dict[str, Any], step: dict[str, Any], extra_args: dict[str, Any]) -> dict[str, Any]:
    from connections.datastore_manager import memcached_executor

    return await asyncio.to_thread(
        memcached_executor.execute_command,
        host=info.get("host"),
        port=info.get("port") or 11211,
        command=step.get("command"),
        extra_args=extra_args,
    )


async def _execute_mongodb_step(info: dict[str, Any], step: dict[str, Any], extra_args: dict[str, Any]) -> dict[str, Any]:
    from connections.datastore_manager import mongo_executor

    args = step.get("args") or {}
    return await asyncio.to_thread(
        mongo_executor.find,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        database=args.get("database") or extra_args.get("database") or "admin",
        collection=args.get("collection") or "system.version",
        filter_doc=args.get("filter") or {},
        projection=args.get("projection"),
        limit=args.get("limit") or 10,
        extra_args=extra_args,
    )


async def _execute_http_style_step(
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    step: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    tool = step.get("tool")
    step_args = step.get("args") or {}
    if tool == "service_probe_request":
        return await _execute_service_probe_step(info, asset_type, protocol, step, step_args, extra_args)
    if tool == "virtualization_api_request":
        return await _execute_virtualization_step(info, asset_type, protocol, step, step_args, extra_args)
    if tool == "storage_api_request" and asset_type in OBJECT_STORAGE_ASSET_TYPES:
        return await _execute_object_storage_step(info, asset_type, step, step_args, extra_args)
    if tool == "storage_api_request":
        return await _execute_storage_platform_step(info, asset_type, step, step_args, extra_args)
    return await _execute_http_api_step(info, asset_type, step, step_args, extra_args)


async def _execute_service_probe_step(
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    step: dict[str, Any],
    step_args: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.service_probe_manager import service_probe_executor

    return await asyncio.to_thread(
        service_probe_executor.execute,
        asset_type=asset_type,
        protocol=protocol,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        extra_args=extra_args,
        operation=step.get("operation") or step_args.get("operation") or "probe",
        path=step.get("path") or step_args.get("path"),
        timeout=step.get("timeout") or step_args.get("timeout"),
    )


async def _execute_virtualization_step(
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    step: dict[str, Any],
    step_args: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.virtualization_manager import virtualization_api_executor

    return await asyncio.to_thread(
        virtualization_api_executor.execute,
        asset_type=asset_type,
        protocol=protocol,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        extra_args=extra_args,
        operation=step.get("operation") or step_args.get("operation"),
        method=step.get("method") or "GET",
        path=step.get("path"),
        headers=step_args.get("headers") or {},
        body=step_args.get("body"),
        timeout=step.get("timeout") or step_args.get("timeout"),
    )


async def _execute_object_storage_step(
    info: dict[str, Any],
    asset_type: str,
    step: dict[str, Any],
    step_args: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.object_storage_manager import object_storage_executor

    return await asyncio.to_thread(
        object_storage_executor.execute,
        asset_type=asset_type,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        extra_args=extra_args,
        operation=step.get("operation") or step_args.get("operation") or "list_buckets",
        bucket=step.get("bucket") or step_args.get("bucket"),
        prefix=step.get("prefix") or step_args.get("prefix"),
        key=step.get("key") or step_args.get("key"),
        max_keys=step.get("max_keys") or step_args.get("max_keys"),
    )


async def _execute_storage_platform_step(
    info: dict[str, Any],
    asset_type: str,
    step: dict[str, Any],
    step_args: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.storage_platform_manager import storage_platform_executor

    return await asyncio.to_thread(
        storage_platform_executor.execute,
        asset_type=asset_type,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        extra_args=extra_args,
        operation=step.get("operation") or step_args.get("operation") or "health",
        method=step.get("method") or step_args.get("method") or "GET",
        path=step.get("path") or step_args.get("path"),
        headers=step_args.get("headers") or {},
        body=step_args.get("body"),
        timeout=step.get("timeout") or step_args.get("timeout"),
    )


async def _execute_http_api_step(
    info: dict[str, Any],
    asset_type: str,
    step: dict[str, Any],
    step_args: dict[str, Any],
    extra_args: dict[str, Any],
) -> dict[str, Any]:
    from connections.http_api_manager import http_api_executor

    return await asyncio.to_thread(
        http_api_executor.request,
        asset_type=asset_type,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        extra_args=extra_args,
        method=step.get("method") or "GET",
        path=step.get("path") or "/",
        headers=step_args.get("headers") or {},
        body=step_args.get("body"),
    )


async def _execute_snmp_step(info: dict[str, Any], step: dict[str, Any], extra_args: dict[str, Any]) -> dict[str, Any]:
    from connections.snmp_manager import snmp_executor

    snmp_extra_args = dict(extra_args)
    if snmp_extra_args.get("v3_auth_user") and not snmp_extra_args.get("v3_username"):
        snmp_extra_args["v3_username"] = snmp_extra_args.get("v3_auth_user")
    elif info.get("username") and not any(
        snmp_extra_args.get(key)
        for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
    ):
        snmp_extra_args.setdefault("v3_username", info.get("username"))
    return await asyncio.to_thread(
        snmp_executor.get,
        host=info.get("host"),
        port=info.get("port") or 161,
        oid=step.get("oid") or "1.3.6.1.2.1.1.1.0",
        extra_args=snmp_extra_args,
    )
