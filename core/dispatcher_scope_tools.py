"""Scope-based batch execution for active asset sessions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from core.asset_protocols import (
    MIDDLEWARE_ASSET_TYPES,
    NETWORK_SSH_ASSET_TYPES,
    STORAGE_SSH_ASSET_TYPES,
    resolve_asset_identity,
)
from core.safety_policy import check_hard_block, check_readonly_block


async def execute_on_scope_tool(args: dict[str, Any], context: dict[str, Any]) -> str:
    scope_target = args.get("scope_target", "ALL")
    command = args.get("command", "")
    blocked, reason = check_readonly_block("execute_on_scope", args, context)
    if blocked:
        from core.tool_policy_response import blocked_tool_response

        return blocked_tool_response("execute_on_scope", args, context, reason)
    if not str(command).strip():
        return json.dumps({"status": "ERROR", "error": "范围执行命令不能为空。"}, ensure_ascii=False)

    from connections.ssh_manager import ssh_manager

    target_tag = context.get("scope_value", "")
    if isinstance(target_tag, str) and target_tag.startswith("[") and target_tag.endswith("]"):
        target_tag = target_tag[1:-1]

    tasks = []
    for session_id, session_data in ssh_manager.active_sessions.items():
        info = session_data["info"]
        identity = resolve_asset_identity(
            info.get("asset_type"),
            info.get("protocol"),
            info.get("extra_args", {}),
            info.get("host"),
            info.get("port"),
            info.get("remark"),
        )
        if identity["protocol"] != "ssh":
            continue

        if target_tag and target_tag not in info.get("tags", []):
            continue

        host = info.get("host")
        remark = info.get("remark", "")
        if scope_target == "ALL" or (host and host in scope_target) or (remark and remark in scope_target):
            tasks.append((session_id, host or remark, identity["asset_type"]))

    if not tasks:
        return json.dumps(
            {
                "error": f"找不到匹配的在线资产会话 (Tag: {target_tag}, Target: {scope_target})。"
            }
        )

    semaphore = asyncio.Semaphore(50)

    async def _run_single(target_session_id: str, target_host: str, target_asset_type: str):
        async with semaphore:
            if target_asset_type in NETWORK_SSH_ASSET_TYPES:
                actual_tool = "network_cli_execute_command"
            elif target_asset_type in STORAGE_SSH_ASSET_TYPES:
                actual_tool = "storage_execute_command"
            elif target_asset_type in MIDDLEWARE_ASSET_TYPES:
                actual_tool = "middleware_execute_command"
            else:
                actual_tool = "linux_execute_command"

            session_info = ssh_manager.active_sessions.get(target_session_id, {}).get("info", {})
            hard_blocked, hard_reason = check_hard_block(actual_tool, args, {**context, **session_info})
            if hard_blocked:
                return target_host, {"success": False, "error": hard_reason}
            readonly_blocked, readonly_reason = check_readonly_block(
                actual_tool, args, {**context, **session_info}
            )
            if readonly_blocked:
                return target_host, {"success": False, "error": readonly_reason}

            if actual_tool == "network_cli_execute_command":
                result = await asyncio.to_thread(
                    ssh_manager.execute_network_cli_command, target_session_id, command
                )
            else:
                result = await asyncio.to_thread(
                    ssh_manager.execute_command, target_session_id, command
                )
            return target_host, result

    completed = await asyncio.gather(
        *(_run_single(session_id, host, asset_type) for session_id, host, asset_type in tasks)
    )

    return json.dumps(
        {
            "status": "BATCH_COMPLETE",
            "total_hosts": len(tasks),
            "unique_outputs": len(_group_scope_outputs(completed)),
            "results": _aggregate_scope_outputs(completed),
        },
        ensure_ascii=False,
    )


def _group_scope_outputs(completed: list[tuple[str, dict]]) -> dict[str, list[str]]:
    results = {}
    for host, result in completed:
        if result.get("success"):
            output = str(result.get("output", ""))
        else:
            output = str(result.get("error", "ERROR"))

        if not output.strip():
            output = "[空输出]"

        if output not in results:
            results[output] = []
        results[output].append(host)
    return results


def _aggregate_scope_outputs(completed: list[tuple[str, dict]]) -> dict[str, Any]:
    results = {}
    sorted_results = sorted(_group_scope_outputs(completed).items(), key=lambda item: len(item[1]), reverse=True)

    for index, (output, hosts) in enumerate(sorted_results, start=1):
        if index > 20:
            results["..."] = {
                "note": f"剩余 {len(sorted_results) - 20} 种不同的输出结果因篇幅限制被折叠。为了保护上下文，建议您优化命令输出(例如只返回关键的 error code 或做 wc -l 统计)。"
            }
            break

        summary_key = f"{len(hosts)} hosts returned this output"
        display_hosts = hosts[:5] + (["..."] if len(hosts) > 5 else [])
        results[summary_key] = {"hosts": display_hosts, "output": output}

    return results
