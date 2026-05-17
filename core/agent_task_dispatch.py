from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any


logger = logging.getLogger(__name__)

TaskRunner = Callable[[str, str, bool], Awaitable[str]]
TaskRunnerWithTask = Callable[[str, str, bool, Mapping[str, Any]], Awaitable[str]]


def _session_mode(allow_modifications: bool) -> str:
    return "readwrite" if allow_modifications else "readonly"


def _permission_boundary(
    *,
    scope: str,
    parent_allow_mod: bool,
    target_allow_mod: bool,
) -> dict[str, Any]:
    effective_allow_mod = bool(parent_allow_mod and target_allow_mod)
    reason = "allowed"
    if not parent_allow_mod:
        reason = "parent_readonly"
    elif not target_allow_mod:
        reason = "target_readonly"
    return {
        "scope": scope,
        "parent_mode": _session_mode(parent_allow_mod),
        "target_mode": _session_mode(target_allow_mod),
        "effective_mode": _session_mode(effective_allow_mod),
        "downgraded": bool(parent_allow_mod and not effective_allow_mod),
        "reason": reason,
    }


def _timeout_label(timeout_seconds: float) -> str:
    timeout_value = float(timeout_seconds)
    return str(int(timeout_value)) if timeout_value.is_integer() else str(timeout_seconds)


def _observability_metadata(task: Mapping[str, Any]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    observability_task_id = str(task.get("observability_task_id") or task.get("task_id") or "").strip()
    investigation_id = str(task.get("investigation_id") or "").strip()
    if observability_task_id:
        metadata["observability_task_id"] = observability_task_id[:120]
    if investigation_id:
        metadata["investigation_id"] = investigation_id[:120]
    return metadata


async def dispatch_group_tasks(
    tasks: list[dict],
    allow_mod: bool,
    *,
    task_runner: TaskRunner,
    task_runner_with_task: TaskRunnerWithTask | None = None,
    active_sessions: Mapping[str, Mapping[str, Any]] | None = None,
    event_logger: logging.Logger | None = None,
    max_concurrency: int = 10,
    timeout_seconds: float = 60.0,
) -> list[dict]:
    """批量调度并执行一组任务。"""
    if active_sessions is None:
        from connections.ssh_manager import ssh_manager

        active_sessions = ssh_manager.active_sessions

    log = event_logger or logger
    timeout_text = _timeout_label(timeout_seconds)
    sem = asyncio.Semaphore(max_concurrency)

    async def run_task(task: dict) -> dict:
        target_sid = task.get("target_session_id")
        task_desc = task.get("task_description")
        dispatch_scope = str(task.get("dispatch_scope") or "group")
        observability_metadata = _observability_metadata(task)

        if not target_sid or not task_desc:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": "Invalid task definition",
                **observability_metadata,
            }

        target_info = active_sessions.get(target_sid, {}).get("info", {})
        target_name = target_info.get("remark") or target_info.get("host") or target_sid
        target_allow_mod = bool(target_info.get("allow_modifications", False))
        permission_boundary = _permission_boundary(
            scope=dispatch_scope,
            parent_allow_mod=bool(allow_mod),
            target_allow_mod=target_allow_mod,
        )
        effective_allow_mod = permission_boundary["effective_mode"] == "readwrite"

        log.warning(
            f"🤖 [Swarm 协同] 指挥官 Agent 正在向子会话 {target_name} ({target_sid}) 下达自然语言任务: {task_desc}"
        )

        try:
            result = await asyncio.wait_for(
                (
                    task_runner_with_task(target_sid, task_desc, effective_allow_mod, task)
                    if task_runner_with_task
                    else task_runner(target_sid, task_desc, effective_allow_mod)
                ),
                timeout=timeout_seconds,
            )
            return {
                "session_id": target_sid,
                "status": "SUCCESS",
                "allow_modifications": effective_allow_mod,
                "session_mode": permission_boundary["effective_mode"],
                "permission_boundary": permission_boundary,
                **observability_metadata,
                "report": result,
            }
        except asyncio.TimeoutError:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": f"跨域协同超时 ({timeout_text}秒) 被强行中断。",
                **observability_metadata,
            }
        except Exception as e:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": f"跨域协同异常: {str(e)}",
                **observability_metadata,
            }

    async def bound_run_task(task: dict) -> dict:
        async with sem:
            return await run_task(task)

    results = await asyncio.gather(*(bound_run_task(task) for task in tasks))
    return list(results)
