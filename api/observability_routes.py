from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schema_models.common import ResponseModel
from core.observability.service import catalog_service


router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/overview", response_model=ResponseModel)
async def get_observability_overview():
    return ResponseModel(status="success", data={"overview": catalog_service.overview()})


@router.get("/systems", response_model=ResponseModel)
async def list_observability_systems():
    return ResponseModel(status="success", data={"systems": catalog_service.list_systems()})


@router.get("/systems/{system_id}", response_model=ResponseModel)
async def get_observability_system_profile(system_id: str):
    profile = catalog_service.get_profile(system_id)
    if not profile:
        raise HTTPException(status_code=404, detail="业务系统画像不存在")
    return ResponseModel(status="success", data={"profile": profile.model_dump()})


@router.get("/sources", response_model=ResponseModel)
async def list_observable_sources():
    return ResponseModel(status="success", data={"sources": catalog_service.list_sources()})


@router.get("/profile-packs", response_model=ResponseModel)
async def list_observability_profile_packs():
    return ResponseModel(status="success", data={"profile_packs": catalog_service.list_profile_packs()})
