from __future__ import annotations

from typing import TypedDict


class HydrateStatus(TypedDict):
    total: int
    done: int
    success: int
    running: bool


HYDRATE_STATUS: HydrateStatus = {
    "total": 0,
    "done": 0,
    "success": 0,
    "running": False,
}


def get_hydrate_status_record() -> HydrateStatus:
    return dict(HYDRATE_STATUS)


def start_hydrate_run(total: int) -> None:
    HYDRATE_STATUS["total"] = total
    HYDRATE_STATUS["done"] = 0
    HYDRATE_STATUS["success"] = 0
    HYDRATE_STATUS["running"] = True


def record_hydrate_success() -> None:
    HYDRATE_STATUS["success"] += 1


def record_hydrate_done() -> None:
    HYDRATE_STATUS["done"] += 1


def finish_hydrate_run() -> None:
    HYDRATE_STATUS["running"] = False
