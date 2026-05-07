import asyncio

from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.assets import (
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
from api.schema_models.assets import (
    AssetPayload,
    BatchAssetGroupDeletePayload,
    BatchAssetGroupPayload,
    BatchAssetGroupRenamePayload,
    BatchAssetImportItem,
)
from api.schema_models.common import ResponseModel
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

DEFAULT_ASSET_GROUP = "未分组"


def _normalize_asset_group_name(group_name: str) -> str:
    return (group_name or "").strip() or DEFAULT_ASSET_GROUP


def _with_primary_asset_group(tags: list[str] | None, group_name: str) -> list[str]:
    normalized = _normalize_asset_group_name(group_name)
    tail: list[str] = []
    seen = {normalized}
    for tag in tags or []:
        clean = str(tag).strip()
        if not clean or clean == DEFAULT_ASSET_GROUP or clean in seen:
            continue
        seen.add(clean)
        tail.append(clean)
    return [normalized, *tail]


def _primary_asset_group(tags: list[str] | None) -> str:
    return _normalize_asset_group_name((tags or [DEFAULT_ASSET_GROUP])[0])


def _rename_primary_asset_group(
    tags: list[str] | None,
    old_group_name: str,
    new_group_name: str,
) -> list[str]:
    if _primary_asset_group(tags) != old_group_name:
        return tags or [DEFAULT_ASSET_GROUP]
    return _with_primary_asset_group(
        [tag for tag in (tags or [])[1:] if _normalize_asset_group_name(tag) != old_group_name],
        new_group_name,
    )


def _delete_asset_group_tags(
    tags: list[str] | None,
    group_name: str,
    fallback_group: str,
) -> list[str]:
    current = tags or [DEFAULT_ASSET_GROUP]
    fallback = _normalize_asset_group_name(fallback_group)
    if _primary_asset_group(current) == group_name:
        return _with_primary_asset_group(
            [tag for tag in current[1:] if _normalize_asset_group_name(tag) != group_name],
            fallback,
        )
    remaining = [
        tag for tag in current
        if _normalize_asset_group_name(tag) != group_name
    ]
    return remaining or [DEFAULT_ASSET_GROUP]


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


@router.post("/assets/groups/bulk", response_model=ResponseModel)
async def bulk_update_asset_group(req: BatchAssetGroupPayload):
    """批量更新资产主分组；主分组与会话组名称保持一致。"""
    group_name = _normalize_asset_group_name(req.group_name)
    asset_ids = [asset_id for asset_id in dict.fromkeys(req.asset_ids) if asset_id > 0]
    if not asset_ids:
        return ResponseModel(status="error", message="请选择要加入分组的资产")

    updated_assets = []
    try:
        for asset_id in asset_ids:
            asset = await asyncio.to_thread(get_saved_asset_record, asset_id)
            asset["tags"] = _with_primary_asset_group(asset.get("tags"), group_name)
            updated = await asyncio.to_thread(update_saved_asset_record, asset_id, asset)
            updated_assets.append(updated)
    except AssetServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(
        status="success",
        data={
            "assets": updated_assets,
            "updated": len(updated_assets),
            "group_name": group_name,
        },
        message=f"已将 {len(updated_assets)} 条资产加入 {group_name}",
    )


@router.post("/assets/groups/rename", response_model=ResponseModel)
async def rename_asset_group(req: BatchAssetGroupRenamePayload):
    """批量改名资产主分组，并返回受影响资产。"""
    group_name = _normalize_asset_group_name(req.group_name)
    new_group_name = _normalize_asset_group_name(req.new_group_name)
    if group_name == new_group_name:
        return ResponseModel(status="error", message="新旧资产组名称相同")

    updated_assets = []
    assets = await asyncio.to_thread(list_saved_asset_records)
    try:
        for asset in assets:
            if _primary_asset_group(asset.get("tags")) != group_name:
                continue
            asset["tags"] = _rename_primary_asset_group(
                asset.get("tags"),
                group_name,
                new_group_name,
            )
            updated = await asyncio.to_thread(update_saved_asset_record, asset["id"], asset)
            updated_assets.append(updated)
    except AssetServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(
        status="success",
        data={
            "assets": updated_assets,
            "updated": len(updated_assets),
            "group_name": new_group_name,
        },
        message=f"资产组已改名：{group_name} -> {new_group_name}",
    )


@router.post("/assets/groups/delete", response_model=ResponseModel)
async def delete_asset_group(req: BatchAssetGroupDeletePayload):
    """删除资产组；主分组命中的资产移动到 fallback_group。"""
    group_name = _normalize_asset_group_name(req.group_name)
    fallback_group = _normalize_asset_group_name(req.fallback_group)
    if group_name == DEFAULT_ASSET_GROUP:
        return ResponseModel(status="error", message="默认资产组不能删除")
    if group_name == fallback_group:
        fallback_group = DEFAULT_ASSET_GROUP

    updated_assets = []
    assets = await asyncio.to_thread(list_saved_asset_records)
    try:
        for asset in assets:
            old_tags = asset.get("tags") or [DEFAULT_ASSET_GROUP]
            new_tags = _delete_asset_group_tags(old_tags, group_name, fallback_group)
            if new_tags == old_tags:
                continue
            asset["tags"] = new_tags
            updated = await asyncio.to_thread(update_saved_asset_record, asset["id"], asset)
            updated_assets.append(updated)
    except AssetServiceError as exc:
        raise_http_error(exc)

    return ResponseModel(
        status="success",
        data={
            "assets": updated_assets,
            "updated": len(updated_assets),
            "group_name": group_name,
            "fallback_group": fallback_group,
        },
        message=f"资产组已删除：{group_name}",
    )


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
