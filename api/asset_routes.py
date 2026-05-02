import asyncio

from fastapi import APIRouter

from api.errors import raise_http_error
from api.mappers import (
    asset_deleted_response_kwargs,
    asset_normalization_applied_response_kwargs,
    asset_normalization_preview_response_kwargs,
    asset_payload,
    asset_response_kwargs,
    asset_saved_response_kwargs,
    asset_types_response_kwargs,
    asset_updated_response_kwargs,
    batch_asset_import_payload,
    batch_asset_import_response_kwargs,
    saved_assets_response_kwargs,
)
from api.schemas import AssetPayload, BatchAssetImportItem, ResponseModel
from core.asset_catalog_response import build_asset_types_response
from core.asset_cleanup_service import (
    apply_asset_cleanup_record,
    build_asset_cleanup_plan_record,
)
from core.asset_protocols import get_asset_catalog
from core.asset_service import (
    AssetServiceError,
    batch_import_asset_records,
    get_saved_asset_record,
    list_saved_asset_records,
    remove_saved_asset_record,
    save_asset_record,
    update_saved_asset_record,
)


router = APIRouter()


@router.get("/assets/saved", response_model=ResponseModel)
async def get_saved_assets():
    """【新功能】获取 SQLite 中持久化的所有资产信息（通讯录）"""
    assets = await asyncio.to_thread(list_saved_asset_records)
    return ResponseModel(**saved_assets_response_kwargs(assets))


@router.post("/assets", response_model=ResponseModel)
async def create_asset(req: AssetPayload):
    """创建或按 host+资产类型+协议更新资产；密码和敏感 extra_args 会加密保存。"""
    await asyncio.to_thread(save_asset_record, asset_payload(req))
    return ResponseModel(**asset_saved_response_kwargs())


def _asset_types_response() -> ResponseModel:
    data = build_asset_types_response(get_asset_catalog())
    return ResponseModel(**asset_types_response_kwargs(data))


@router.get("/assets/types", response_model=ResponseModel)
async def get_asset_types():
    """返回后端认可的资产类型与默认登录协议目录。"""
    return _asset_types_response()


@router.get("/assets/{asset_id}", response_model=ResponseModel)
async def get_asset(asset_id: int):
    """查询单个资产详情；响应会脱敏密码和敏感 extra_args。"""
    try:
        asset = await asyncio.to_thread(get_saved_asset_record, asset_id)
    except AssetServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**asset_response_kwargs(asset))


@router.put("/assets/{asset_id}", response_model=ResponseModel)
async def update_asset(asset_id: int, req: AssetPayload):
    """按资产 ID 修改资产；传入 ******** 会保留原密码/密钥。"""
    try:
        asset = await asyncio.to_thread(
            update_saved_asset_record,
            asset_id,
            asset_payload(req),
        )
    except AssetServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**asset_updated_response_kwargs(asset))


@router.get("/assets/normalize/preview", response_model=ResponseModel)
async def preview_asset_normalization():
    """预览资产协议、host/port 与重复数据清理计划。"""
    plan = await asyncio.to_thread(build_asset_cleanup_plan_record)
    return ResponseModel(**asset_normalization_preview_response_kwargs(plan))


@router.post("/assets/normalize/apply", response_model=ResponseModel)
async def apply_asset_normalization():
    """执行资产规范化清理；执行前会生成本地备份文件。"""
    report = await asyncio.to_thread(apply_asset_cleanup_record)
    return ResponseModel(**asset_normalization_applied_response_kwargs(report))


@router.delete("/assets/{asset_id}", response_model=ResponseModel)
async def delete_saved_asset(asset_id: int):
    """【新功能】删除持久化的资产"""
    await asyncio.to_thread(remove_saved_asset_record, asset_id)
    return ResponseModel(**asset_deleted_response_kwargs())


@router.post("/assets/batch_import", response_model=ResponseModel)
async def batch_import_assets(items: list[BatchAssetImportItem]):
    """【#25 新功能】批量导入资产到金库（通讯录），支持 JSON 数组格式"""
    try:
        result = await asyncio.to_thread(
            batch_import_asset_records,
            batch_asset_import_payload(items),
        )
    except AssetServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(**batch_asset_import_response_kwargs(result))
