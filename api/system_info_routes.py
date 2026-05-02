from fastapi import APIRouter

from api.mappers import system_info_response_kwargs
from api.schemas import ResponseModel
from core.database_capabilities_service import (
    get_database_driver_capabilities_record,
    get_oracle_client_config_record,
)
from core.hydration_status_service import get_hydrate_status_record


router = APIRouter()


@router.get("/oracle/client-config", response_model=ResponseModel)
async def get_oracle_client_config():
    """返回本机 Oracle Instant Client 自动探测结果，供前端填充 Thick Mode 配置。"""
    data = get_oracle_client_config_record()
    return ResponseModel(**system_info_response_kwargs(data))


@router.get("/database/driver-capabilities", response_model=ResponseModel)
async def get_database_driver_capabilities_api():
    """返回数据库连接器、Python 包和外部客户端安装状态。"""
    data = get_database_driver_capabilities_record()
    return ResponseModel(**system_info_response_kwargs(data))


@router.get("/hydrate/status", response_model=ResponseModel)
async def get_hydrate_status():
    """【新功能】获取启动时资产重连的进度，前端可轮询此接口展示启动状态"""
    return ResponseModel(**system_info_response_kwargs(get_hydrate_status_record()))
