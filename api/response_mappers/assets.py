from __future__ import annotations

from typing import Any

from api.schema_models.assets import AssetPayload, BatchAssetImportItem


def asset_payload(req: AssetPayload) -> dict[str, Any]:
    return req.model_dump()


def batch_asset_import_payload(items: list[BatchAssetImportItem]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]


def saved_assets_response_kwargs(assets: list[Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"assets": assets},
    }


def asset_saved_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已保存",
    }


def asset_types_response_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
    }


def asset_response_kwargs(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {"asset": asset},
    }


def asset_updated_response_kwargs(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已更新",
        "data": {"asset": asset},
    }


def asset_deleted_response_kwargs() -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产已成功移除金库。",
    }


def batch_asset_import_response_kwargs(result: dict[str, int]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": f"成功导入 {result['imported']}/{result['total']} 条资产。",
    }


def asset_normalization_preview_response_kwargs(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "data": plan,
    }


def asset_normalization_applied_response_kwargs(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "资产规范化清理完成",
        "data": report,
    }
