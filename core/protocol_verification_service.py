from __future__ import annotations

import asyncio
from typing import Any

from core.protocol_verification import (
    build_asset_matrix,
    build_overview,
    list_verification_runs,
    run_asset_verification,
)


class ProtocolVerificationServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def build_protocol_verification_overview(memory_db) -> dict[str, Any]:
    return build_overview(memory_db.get_all_assets())


def get_protocol_verification_asset(memory_db, asset_id: int) -> dict[str, Any]:
    asset = memory_db.get_asset(asset_id)
    if not asset:
        raise ProtocolVerificationServiceError(404, "资产不存在")
    return asset


def build_protocol_verification_matrix(memory_db, asset_id: int) -> dict[str, Any]:
    return build_asset_matrix(get_protocol_verification_asset(memory_db, asset_id))


async def run_protocol_verification_for_asset(memory_db, asset_id: int) -> dict[str, Any]:
    asset = await asyncio.to_thread(get_protocol_verification_asset, memory_db, asset_id)
    return await run_asset_verification(asset)


def list_protocol_verification_run_records(asset_id: int, limit: int = 20) -> list[dict[str, Any]]:
    return list_verification_runs(asset_id=asset_id, limit=limit)
