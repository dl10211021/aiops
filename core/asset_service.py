from __future__ import annotations

from typing import Any

from core.asset_responses import mask_asset_response, mask_asset_responses
from core import memory as memory_module


class AssetServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def _invalidate_asset_derived_caches(memory_db: Any | None = None) -> None:
    if memory_db is not None:
        return
    from core.protocol_verification_service import invalidate_protocol_verification_overview_cache

    invalidate_protocol_verification_overview_cache()


def list_saved_asset_records(memory_db: Any | None = None) -> list[dict[str, Any]]:
    store = _resolve_memory_db(memory_db)
    assets = store.get_all_assets()
    return mask_asset_responses(assets, store.sensitive_keys)


def save_asset_record(payload: dict[str, Any], memory_db: Any | None = None) -> None:
    store = _resolve_memory_db(memory_db)
    store.save_asset(
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
    _invalidate_asset_derived_caches(memory_db)


def get_saved_asset_record(asset_id: int, memory_db: Any | None = None) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    asset = store.get_asset(asset_id)
    if not asset:
        raise AssetServiceError(404, "资产不存在")
    return mask_asset_response(asset, store.sensitive_keys)


def update_saved_asset_record(
    asset_id: int,
    payload: dict[str, Any],
    memory_db: Any | None = None,
) -> dict[str, Any]:
    store = _resolve_memory_db(memory_db)
    asset = store.update_asset(asset_id, payload)
    if not asset:
        raise AssetServiceError(404, "资产不存在")
    _invalidate_asset_derived_caches(memory_db)
    return mask_asset_response(asset, store.sensitive_keys)


def remove_saved_asset_record(asset_id: int, memory_db: Any | None = None) -> None:
    store = _resolve_memory_db(memory_db)
    store.delete_asset(asset_id)
    _invalidate_asset_derived_caches(memory_db)


def batch_import_asset_records(
    items: list[dict[str, Any]],
    memory_db: Any | None = None,
) -> dict[str, int]:
    if not items:
        raise AssetServiceError(422, "批量导入资产列表不能为空。")
    store = _resolve_memory_db(memory_db)
    try:
        store.save_assets_batch(items)
    except Exception as exc:
        raise AssetServiceError(500, f"批量导入资产失败: {exc}") from exc
    _invalidate_asset_derived_caches(memory_db)
    return {"imported": len(items), "total": len(items)}
