"""HTTP/API style tool execution for the skill dispatcher."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from core.safety_policy import check_readonly_block
from core.tool_policy_response import blocked_tool_response

HTTP_API_TOOL_NAMES = {
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
}
API_TOOL_NAMES = {"service_probe_request"} | HTTP_API_TOOL_NAMES
OBJECT_STORAGE_ASSET_TYPES = {"s3", "minio", "oss", "cos", "obs", "object_storage"}


async def execute_api_tool(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    route_callback: Callable[[str, dict[str, Any], dict[str, Any]], Awaitable[str]] | None = None,
) -> str:
    if tool_call_name == "service_probe_request":
        return await _execute_service_probe(tool_call_name, args, context)
    if tool_call_name == "virtualization_api_request":
        return await _execute_virtualization_api(tool_call_name, args, context)
    if tool_call_name == "storage_api_request":
        return await _execute_storage_api(tool_call_name, args, context, route_callback)
    if tool_call_name in HTTP_API_TOOL_NAMES:
        return await _execute_http_api(tool_call_name, args, context)
    return '{"error": "Unknown API tool"}'


async def _execute_service_probe(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.service_probe_manager import service_probe_executor

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        service_probe_executor.execute,
        asset_type=context.get("asset_type") or "",
        protocol=context.get("protocol") or context.get("asset_type") or "",
        host=context.get("host") or "",
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        extra_args=context.get("extra_args") or {},
        operation=args.get("operation") or "probe",
        path=args.get("path"),
        timeout=args.get("timeout"),
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_virtualization_api(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    if context.get("protocol") == "winrm":
        return json.dumps(
            {
                "status": "ERROR",
                "error": "当前资产通过 WinRM 管理，不是虚拟化 HTTP API；请使用 winrm_execute_command 执行明确的 Hyper-V PowerShell 命令。",
            },
            ensure_ascii=False,
        )

    from connections.virtualization_manager import virtualization_api_executor

    method = str(args.get("method") or "GET").upper()
    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        virtualization_api_executor.execute,
        asset_type=context.get("asset_type") or "",
        protocol=context.get("protocol") or "",
        host=context.get("host") or "",
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        extra_args=context.get("extra_args") or {},
        operation=args.get("operation"),
        method=method,
        path=args.get("path"),
        headers=args.get("headers") or {},
        body=args.get("body"),
        timeout=args.get("timeout"),
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_storage_api(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    route_callback: Callable[[str, dict[str, Any], dict[str, Any]], Awaitable[str]] | None,
) -> str:
    if context.get("protocol") == "snmp":
        if route_callback is None:
            return json.dumps({"error": "storage_api_request SNMP fallback requires route callback"}, ensure_ascii=False)
        return await route_callback(
            "snmp_get",
            {"oid": args.get("oid") or "1.3.6.1.2.1.1.1.0"},
            context,
        )

    asset_type = str(context.get("asset_type") or "").strip().lower()
    sub_type = str((context.get("extra_args") or {}).get("sub_type") or "").strip().lower()
    if asset_type in OBJECT_STORAGE_ASSET_TYPES or sub_type in OBJECT_STORAGE_ASSET_TYPES:
        return await _execute_object_storage(tool_call_name, args, context)
    return await _execute_storage_platform(tool_call_name, args, context)


async def _execute_object_storage(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.object_storage_manager import object_storage_executor

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        object_storage_executor.execute,
        asset_type=context.get("asset_type") or "",
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        extra_args=context.get("extra_args") or {},
        operation=args.get("operation") or "list_buckets",
        bucket=args.get("bucket"),
        prefix=args.get("prefix"),
        key=args.get("key"),
        max_keys=args.get("max_keys"),
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_storage_platform(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.storage_platform_manager import storage_platform_executor

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        storage_platform_executor.execute,
        asset_type=context.get("asset_type") or "",
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        extra_args=context.get("extra_args") or {},
        operation=args.get("operation") or "health",
        method=args.get("method") or "GET",
        path=args.get("path"),
        headers=args.get("headers") or {},
        body=args.get("body"),
        timeout=args.get("timeout"),
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _execute_http_api(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
) -> str:
    from connections.http_api_manager import http_api_executor

    method = str(args.get("method") or "GET").upper()
    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        http_api_executor.request,
        asset_type=context.get("asset_type") or "",
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username") or "",
        password=context.get("password"),
        extra_args=context.get("extra_args") or {},
        method=method,
        path=args.get("path") or "/",
        headers=args.get("headers") or {},
        body=args.get("body"),
    )
    return json.dumps(result, ensure_ascii=False, default=str)
