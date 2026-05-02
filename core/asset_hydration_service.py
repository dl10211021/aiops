from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.hydration_status_service import (
    finish_hydrate_run,
    record_hydrate_done,
    record_hydrate_success,
    start_hydrate_run,
)


def _resolve_memory_db(memory_db=None):
    if memory_db is not None:
        return memory_db
    from core.memory import memory_db as default_memory_db

    return default_memory_db


def _resolve_ssh_manager(ssh_manager=None):
    if ssh_manager is not None:
        return ssh_manager
    from connections.ssh_manager import ssh_manager as default_ssh_manager

    return default_ssh_manager


async def hydrate_assets(
    memory_db=None,
    ssh_manager=None,
    logger: logging.Logger | None = None,
) -> None:
    """Reconnect persisted assets during startup without blocking app creation."""
    memory_db = _resolve_memory_db(memory_db)
    ssh_manager = _resolve_ssh_manager(ssh_manager)
    logger = logger or logging.getLogger(__name__)

    assets = await asyncio.to_thread(memory_db.get_all_assets)
    start_hydrate_run(len(assets) if assets else 0)

    async def _connect_single(asset: dict[str, Any]):
        try:
            await asyncio.to_thread(
                ssh_manager.connect,
                host=asset["host"],
                port=asset["port"] or 22,
                username=asset["username"] or "",
                password=asset["password"],
                allow_modifications=False,
                active_skills=asset["skills"],
                agent_profile=asset["agent_profile"],
                remark=asset["remark"],
                asset_type=asset.get("asset_type", "ssh"),
                protocol=asset.get("protocol"),
                extra_args=asset["extra_args"],
                tags=asset.get("tags", ["未分组"]),
                lazy=True,
            )
            record_hydrate_success()
            return True
        except Exception as exc:
            logger.error(f"Auto-hydrate failed for {asset['host']}: {exc}")
            return False
        finally:
            record_hydrate_done()

    if assets:
        results = await asyncio.gather(*[_connect_single(asset) for asset in assets])
        success_count = sum(1 for result in results if result)
        logger.info(
            f"Auto-hydrated {success_count}/{len(assets)} assets from database in background."
        )

    finish_hydrate_run()
