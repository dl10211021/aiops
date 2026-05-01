from __future__ import annotations

from typing import Any

from core.asset_responses import mask_asset_response, mask_asset_responses


class AssetServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_saved_asset_records(memory_db) -> list[dict[str, Any]]:
    assets = memory_db.get_all_assets()
    return mask_asset_responses(assets, memory_db.sensitive_keys)


def save_asset_record(memory_db, payload: dict[str, Any]) -> None:
    memory_db.save_asset(
        payload.get("remark") or "",
        payload.get("host"),
        payload.get("port"),
        payload.get("username"),
        payload.get("password"),
        payload.get("asset_type"),
        payload.get("agent_profile"),
        payload.get("extra_args") or {},
        payload.get("skills") or [],
        payload.get("tags") or [],
        payload.get("protocol"),
    )


def get_saved_asset_record(memory_db, asset_id: int) -> dict[str, Any]:
    asset = memory_db.get_asset(asset_id)
    if not asset:
        raise AssetServiceError(404, "资产不存在")
    return mask_asset_response(asset, memory_db.sensitive_keys)


def update_saved_asset_record(memory_db, asset_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    asset = memory_db.update_asset(asset_id, payload)
    if not asset:
        raise AssetServiceError(404, "资产不存在")
    return mask_asset_response(asset, memory_db.sensitive_keys)


def remove_saved_asset_record(memory_db, asset_id: int) -> None:
    memory_db.delete_asset(asset_id)


def batch_import_asset_records(memory_db, items: list[dict[str, Any]]) -> dict[str, int]:
    if not items:
        raise AssetServiceError(422, "批量导入资产列表不能为空。")
    try:
        memory_db.save_assets_batch(items)
    except Exception as exc:
        raise AssetServiceError(500, f"批量导入资产失败: {exc}") from exc
    return {"imported": len(items), "total": len(items)}
