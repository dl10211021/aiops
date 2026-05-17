from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any


logger = logging.getLogger(__name__)

TaskRunner = Callable[[str, str, bool], Awaitable[str]]


def _timeout_label(timeout_seconds: float) -> str:
    timeout_value = float(timeout_seconds)
    return str(int(timeout_value)) if timeout_value.is_integer() else str(timeout_seconds)


async def dispatch_group_tasks(
    tasks: list[dict],
    allow_mod: bool,
    *,
    task_runner: TaskRunner,
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

        if not target_sid or not task_desc:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": "Invalid task definition",
            }

        target_info = active_sessions.get(target_sid, {}).get("info", {})
        target_name = target_info.get("remark") or target_info.get("host") or target_sid
        effective_allow_mod = bool(allow_mod and target_info.get("allow_modifications", False))

        log.warning(
            f"🤖 [Swarm 协同] 指挥官 Agent 正在向子会话 {target_name} ({target_sid}) 下达自然语言任务: {task_desc}"
        )

        try:
            result = await asyncio.wait_for(
                task_runner(target_sid, task_desc, effective_allow_mod),
                timeout=timeout_seconds,
            )
            return {
                "session_id": target_sid,
                "status": "SUCCESS",
                "allow_modifications": effective_allow_mod,
                "session_mode": "readwrite" if effective_allow_mod else "readonly",
                "report": result,
            }
        except asyncio.TimeoutError:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": f"跨域协同超时 ({timeout_text}秒) 被强行中断。",
            }
        except Exception as e:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": f"跨域协同异常: {str(e)}",
            }

    async def bound_run_task(task: dict) -> dict:
        async with sem:
            return await run_task(task)

    results = await asyncio.gather(*(bound_run_task(task) for task in tasks))
    return list(results)
