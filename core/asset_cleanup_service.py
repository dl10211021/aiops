from __future__ import annotations

from typing import Any

from core import asset_cleanup


def build_asset_cleanup_plan_record() -> dict[str, Any]:
    return asset_cleanup.build_asset_cleanup_plan()


def apply_asset_cleanup_record() -> dict[str, Any]:
    return asset_cleanup.apply_asset_cleanup()
