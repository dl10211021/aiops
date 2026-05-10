"""Protocol and session-backed tool execution for the dispatcher."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from core.asset_protocols import (
    MIDDLEWARE_ASSET_TYPES,
    NETWORK_SSH_ASSET_TYPES,
    STORAGE_SSH_ASSET_TYPES,
    resolve_asset_identity,
)
from core.safety_policy import check_readonly_block
from core.tool_policy_response import blocked_tool_response

SSH_COMMAND_TOOL_NAMES = {
    "linux_execute_command",
    "container_execute_command",
    "middleware_execute_command",
    "storage_execute_command",
}
SESSION_TOOL_NAMES = SSH_COMMAND_TOOL_NAMES | {
    "winrm_execute_command",
    "network_cli_execute_command",
    "snmp_get",
    "list_active_sessions",
    "dispatch_sub_agents",
}

async def execute_session_tool(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    if tool_call_name in SSH_COMMAND_TOOL_NAMES:
        return await _execute_ssh_command(tool_call_name, args, context)
    if tool_call_name == "winrm_execute_command":
        return await _execute_winrm_command(tool_call_name, args, context, log)
    if tool_call_name == "network_cli_execute_command":
        return await _execute_network_cli_command(tool_call_name, args, context)
    if tool_call_name == "snmp_get":
        return await _execute_snmp_get(args, context)
    if tool_call_name == "list_active_sessions":
        return await _list_active_sessions(log)
    if tool_call_name == "dispatch_sub_agents":
        return await _dispatch_sub_agents(args, context)
    return '{"error": "Unknown session tool"}'


async def _execute_ssh_command(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> str:
    from connections.ssh_manager import ssh_manager

    identity = resolve_asset_identity(
        context.get("asset_type"),
        context.get("protocol"),
        context.get("extra_args") or {},
        context.get("host"),
        context.get("port"),
        context.get("remark"),
    )
    if identity["protocol"] != "ssh":
        return json.dumps(
            {"status": "ERROR", "error": f"当前资产协议是 {identity['protocol']}，不能使用 {tool_call_name}；请使用对应的原生协议工具。"},
            ensure_ascii=False,
        )
    if identity["asset_type"] in NETWORK_SSH_ASSET_TYPES:
        return json.dumps(
            {
                "status": "ERROR",
                "error": "当前资产是网络设备，不能使用 Linux 命令工具；请使用 network_cli_execute_command。",
            },
            ensure_ascii=False,
        )
    if tool_call_name == "linux_execute_command" and identity["asset_type"] in STORAGE_SSH_ASSET_TYPES:
        return json.dumps(
            {
                "status": "ERROR",
                "error": "当前资产是存储节点，不能使用通用 Linux 命令工具；请使用 storage_execute_command。",
            },
            ensure_ascii=False,
        )
    if tool_call_name == "linux_execute_command" and identity["asset_type"] in MIDDLEWARE_ASSET_TYPES:
        return json.dumps(
            {
                "status": "ERROR",
                "error": "当前资产是中间件主机，不能使用通用 Linux 命令工具；请使用 middleware_execute_command。",
            },
            ensure_ascii=False,
        )
    if tool_call_name == "storage_execute_command" and identity["asset_type"] not in STORAGE_SSH_ASSET_TYPES:
        return json.dumps(
            {
                "status": "ERROR",
                "error": "storage_execute_command 仅用于 Ceph/NFS/NAS/HDFS/GlusterFS 等存储节点；当前资产请使用对应协议工具。",
            },
            ensure_ascii=False,
        )
    if tool_call_name == "middleware_execute_command" and identity["asset_type"] not in MIDDLEWARE_ASSET_TYPES:
        return json.dumps(
            {
                "status": "ERROR",
                "error": "middleware_execute_command 仅用于 Nginx/Tomcat/Kafka/RocketMQ/ZooKeeper/进程等中间件主机；当前资产请使用对应协议工具。",
            },
            ensure_ascii=False,
        )

    session_id = context.get("session_id")
    if not session_id:
        return '{"error": "没有找到激活的远程会话"}'

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(ssh_manager.execute_command, session_id, args.get("command"))
    return json.dumps(result)


async def _execute_winrm_command(
    tool_call_name: str,
    args: dict[str, Any],
    context: dict[str, Any],
    logger: logging.Logger,
) -> str:
    from connections.winrm_manager import winrm_executor

    extra_args = context.get("extra_args") or {}
    command = args.get("command")
    if args.get("password") or args.get("username"):
        logger.warning("winrm_execute_command ignored model-supplied credentials and used managed session credentials.")

    if not all([context.get("host"), context.get("port"), context.get("username"), context.get("password") is not None, command]):
        return json.dumps(
            {
                "status": "ERROR",
                "error": "WinRM 会话凭据不完整，请检查资产中心配置的 host/port/user/password。",
            },
            ensure_ascii=False,
        )

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        winrm_executor.execute_command,
        host=context.get("host"),
        port=context.get("port"),
        username=context.get("username"),
        password=context.get("password"),
        command=command,
        extra_args=extra_args,
    )
    return json.dumps(result, ensure_ascii=False)


async def _execute_network_cli_command(tool_call_name: str, args: dict[str, Any], context: dict[str, Any]) -> str:
    from connections.ssh_manager import ssh_manager

    session_id = context.get("session_id")
    if not session_id:
        return '{"error": "没有找到激活的网络设备会话"}'

    blocked, reason = check_readonly_block(tool_call_name, args, context)
    if blocked:
        return blocked_tool_response(tool_call_name, args, context, reason)

    result = await asyncio.to_thread(
        ssh_manager.execute_network_cli_command,
        session_id,
        args.get("command"),
    )
    return json.dumps(result, ensure_ascii=False)


async def _execute_snmp_get(args: dict[str, Any], context: dict[str, Any]) -> str:
    from connections.snmp_manager import snmp_executor

    extra_args = dict(context.get("extra_args") or {})
    if extra_args.get("v3_auth_user") and not extra_args.get("v3_username"):
        extra_args["v3_username"] = extra_args.get("v3_auth_user")
    elif context.get("username") and not any(
        extra_args.get(key)
        for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
    ):
        extra_args.setdefault("v3_username", context.get("username"))
    result = await asyncio.to_thread(
        snmp_executor.get,
        host=context.get("host"),
        port=context.get("port") or 161,
        oid=args.get("oid"),
        extra_args=extra_args,
    )
    return json.dumps(result, ensure_ascii=False, default=str)


async def _list_active_sessions(logger: logging.Logger) -> str:
    from connections.ssh_manager import ssh_manager

    sessions_info = []
    for sid, sdata in list(ssh_manager.active_sessions.items()):
        info = sdata["info"]
        sessions_info.append(
            {
                "session_id": sid,
                "host": info.get("host"),
                "remark": info.get("remark", ""),
                "asset_type": info.get("asset_type"),
                "protocol": info.get("protocol"),
                "profile": info.get("agent_profile", ""),
                "allow_modifications": info.get("allow_modifications", False),
            }
        )
    logger.info(f"总控 Agent 请求了活跃资产列表，当前在线: {len(sessions_info)} 台")
    return json.dumps({"active_sessions": sessions_info}, ensure_ascii=False)


async def _dispatch_sub_agents(args: dict[str, Any], context: dict[str, Any]) -> str:
    from core.agent import dispatch_group_tasks

    tasks = args.get("tasks", [])
    parent_allow_mod = context.get("allow_modifications", False)
    results = await dispatch_group_tasks(tasks, parent_allow_mod)
    return json.dumps({"status": "BATCH_COMPLETE", "results": results}, ensure_ascii=False)
