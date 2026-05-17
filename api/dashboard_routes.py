import asyncio

from fastapi import APIRouter

from connections.ssh_manager import ssh_manager
from api.response_mappers.system import dashboard_response_kwargs
from api.schema_models.common import ResponseModel
from core.dashboard_service import (
    build_dashboard_alert_trend_payload,
    build_dashboard_inspection_run_trend_payload,
    build_dashboard_overview_payload,
    build_dashboard_risk_ranking_payload,
    build_run_trace_audit_export_payload,
)
from core.tool_registry import tool_registry


router = APIRouter()


@router.get("/dashboard/overview", response_model=ResponseModel)
async def get_dashboard_overview():
    """大屏总览接口：资产、在线会话、协议、分类和基础风险计数。"""
    data = await asyncio.to_thread(
        build_dashboard_overview_payload,
        ssh_manager.active_sessions,
    )
    return ResponseModel(**dashboard_response_kwargs(data))


@router.get("/dashboard/toolsets", response_model=ResponseModel)
async def get_dashboard_toolsets():
    """大屏/配置页工具集接口：展示平台工具覆盖度。"""
    catalog = tool_registry.catalog()
    return ResponseModel(**dashboard_response_kwargs(catalog))


@router.get("/dashboard/run-trace-audit/export", response_model=ResponseModel)
async def export_dashboard_run_trace_audit():
    data = await asyncio.to_thread(
        build_run_trace_audit_export_payload,
        ssh_manager.active_sessions,
    )
    return ResponseModel(**dashboard_response_kwargs(data))


@router.get("/dashboard/alerts/trend", response_model=ResponseModel)
async def get_dashboard_alert_trend():
    """大屏告警趋势接口，按日期聚合告警数量和严重级别。"""
    data = await asyncio.to_thread(build_dashboard_alert_trend_payload)
    return ResponseModel(**dashboard_response_kwargs(data))


@router.get("/dashboard/risk-ranking", response_model=ResponseModel)
async def get_dashboard_risk_ranking():
    """大屏风险排行接口，当前按告警数量和严重度聚合主机风险。"""
    data = await asyncio.to_thread(build_dashboard_risk_ranking_payload)
    return ResponseModel(**dashboard_response_kwargs(data))


@router.get("/dashboard/inspection-runs/trend", response_model=ResponseModel)
async def get_dashboard_inspection_run_trend():
    data = await asyncio.to_thread(build_dashboard_inspection_run_trend_payload)
    return ResponseModel(**dashboard_response_kwargs(data))
