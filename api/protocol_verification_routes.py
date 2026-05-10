import asyncio

from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.protocols import (
    asset_verification_matrix_response_kwargs,
    asset_verification_run_response_kwargs,
    asset_verification_runs_response_kwargs,
    protocol_verification_overview_response_kwargs,
)
from api.schema_models.common import ResponseModel
from core.protocol_verification_service import (
    ProtocolVerificationServiceError,
    build_protocol_verification_matrix,
    build_protocol_verification_overview,
    build_protocol_verification_status_overview,
    list_protocol_verification_run_records,
    run_protocol_verification_for_asset,
)


router = APIRouter()


@router.get("/verification/protocols")
async def get_protocol_verification_overview():
    """返回全量资产协议验证矩阵概览，不包含任何敏感凭据。"""
    data = await asyncio.to_thread(build_protocol_verification_overview)
    return ResponseModel(**protocol_verification_overview_response_kwargs(data))


@router.get("/verification/protocols/status")
async def get_protocol_verification_status_overview():
    """返回资产列表页使用的轻量协议验证状态，不包含完整矩阵详情。"""
    data = await asyncio.to_thread(build_protocol_verification_status_overview)
    return ResponseModel(**protocol_verification_overview_response_kwargs(data))


@router.get("/assets/{asset_id}/verification", response_model=ResponseModel)
async def get_asset_verification_matrix(asset_id: int):
    """返回单资产协议验证矩阵，不包含任何敏感凭据。"""
    try:
        matrix = await asyncio.to_thread(build_protocol_verification_matrix, asset_id)
    except ProtocolVerificationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**asset_verification_matrix_response_kwargs(matrix))


@router.post("/assets/{asset_id}/verify", response_model=ResponseModel)
async def verify_asset(asset_id: int):
    """执行单资产只读端到端验证，并持久化验证历史。"""
    try:
        run = await run_protocol_verification_for_asset(asset_id)
    except ProtocolVerificationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**asset_verification_run_response_kwargs(run))


@router.get("/assets/{asset_id}/verification/runs", response_model=ResponseModel)
async def list_asset_verification_runs(asset_id: int, limit: int = 20):
    """查询单资产验证历史。"""
    runs = await asyncio.to_thread(list_protocol_verification_run_records, asset_id, limit)
    return ResponseModel(**asset_verification_runs_response_kwargs(runs))
