from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from core.asset_hydration_service import hydrate_assets


TaskScheduler = Callable[[Awaitable[None]], Any]
HeartbeatStarter = Callable[[], None]
HydrationRunner = Callable[[], Awaitable[None]]
RetentionRunner = Callable[[], Awaitable[Any]]


def _resolve_heartbeat_starter(heartbeat_starter: HeartbeatStarter | None = None) -> HeartbeatStarter:
    if heartbeat_starter is not None:
        return heartbeat_starter
    from core.heartbeat import start_heartbeat

    return start_heartbeat


def _resolve_cron_manager(cron_manager=None):
    if cron_manager is not None:
        return cron_manager
    from core.cron_manager import CronManager

    return CronManager


def _resolve_retention_runner(retention_runner: RetentionRunner | None = None) -> RetentionRunner:
    if retention_runner is not None:
        return retention_runner
    from core.session_retention import session_retention_maintenance_loop

    return session_retention_maintenance_loop


def start_app_services(
    *,
    task_scheduler: TaskScheduler = asyncio.create_task,
    heartbeat_starter: HeartbeatStarter | None = None,
    cron_manager=None,
    hydration_runner: HydrationRunner = hydrate_assets,
    retention_runner: RetentionRunner | None = None,
    logger: logging.Logger | None = None,
) -> Any:
    logger = logger or logging.getLogger(__name__)
    heartbeat_starter = _resolve_heartbeat_starter(heartbeat_starter)
    cron_manager = _resolve_cron_manager(cron_manager)
    retention_runner = _resolve_retention_runner(retention_runner)

    heartbeat_starter()
    logger.info("Heartbeat worker started.")
    cron_manager.start_scheduler()
    task_scheduler(retention_runner())
    return task_scheduler(hydration_runner())


def stop_app_services(logger: logging.Logger | None = None) -> None:
    logger = logger or logging.getLogger(__name__)
    logger.info("OpsCore Backend shutting down...")
    try:
        from core.realtime_canvas import realtime_canvas_manager

        for task in list(realtime_canvas_manager._tasks.values()):
            task.cancel()
    except Exception:
        logger.debug("Realtime canvas shutdown cleanup skipped.", exc_info=True)
