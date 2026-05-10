from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.schema_models.common import ResponseModel
from core.observability.service import catalog_service


router = APIRouter(prefix="/observability", tags=["observability"])


class InvestigationCreateRequest(BaseModel):
    system_id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=160)
    symptom: str = Field(..., min_length=1, max_length=600)
    time_window: str = Field(default="", max_length=120)
    severity: str = Field(default="unknown", pattern="^(unknown|info|warning|critical)$")


class EvidenceAppendRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    summary: str = Field(default="", max_length=1000)
    evidence_type: str = Field(default="manual", min_length=1, max_length=80)
    task_id: str | None = Field(default=None, max_length=120)
    component_id: str | None = Field(default=None, max_length=120)
    source_id: str | None = Field(default=None, max_length=120)
    raw_ref: str = Field(default="", max_length=240)
    raw_excerpt: str = Field(default="", max_length=1200)
    tool_evidence: dict = Field(default_factory=dict)
    confidence: str = Field(default="pending_review", pattern="^(confirmed|inferred|unknown|pending_review)$")


class RootCauseAppendRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    likelihood: str = Field(default="unknown", max_length=40)
    impact: str = Field(default="unknown", max_length=40)
    confidence: str = Field(default="pending_review", pattern="^(confirmed|inferred|unknown|pending_review)$")
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class AssetBindingRequest(BaseModel):
    asset: dict = Field(default_factory=dict)


class SessionBindingRequest(BaseModel):
    session: dict = Field(default_factory=dict)
    role: str = Field(default="investigation_channel", max_length=80)


class ComponentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    component_type: str | None = Field(default=None, max_length=80)
    layer: str | None = Field(default=None, max_length=80)
    workload_family: str | None = Field(default=None, max_length=80)
    profile_pack_id: str | None = Field(default=None, max_length=120)
    environment: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=40)
    confidence: str | None = Field(default=None, pattern="^(confirmed|inferred|unknown|pending_review)$")
    metadata: dict = Field(default_factory=dict)


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


@router.post("/systems/{system_id}/assets", response_model=ResponseModel)
async def bind_observability_asset(system_id: str, req: AssetBindingRequest):
    profile = catalog_service.bind_asset(system_id, req.asset)
    if not profile:
        raise HTTPException(status_code=404, detail="业务系统画像不存在")
    return ResponseModel(status="success", data={"profile": profile.model_dump(), "summary": profile.summary()})


@router.post("/systems/{system_id}/sessions", response_model=ResponseModel)
async def bind_observability_session(system_id: str, req: SessionBindingRequest):
    profile = catalog_service.bind_session(system_id, req.session, role=req.role)
    if not profile:
        raise HTTPException(status_code=404, detail="业务系统画像不存在或会话无效")
    return ResponseModel(status="success", data={"profile": profile.model_dump(), "summary": profile.summary()})


@router.delete("/systems/{system_id}/components/{component_id}", response_model=ResponseModel)
async def unbind_observability_component(system_id: str, component_id: str):
    profile = catalog_service.unbind_component(system_id, component_id)
    if not profile:
        raise HTTPException(status_code=404, detail="业务系统画像或绑定入口不存在")
    return ResponseModel(status="success", data={"profile": profile.model_dump(), "summary": profile.summary()})


@router.patch("/systems/{system_id}/components/{component_id}", response_model=ResponseModel)
async def update_observability_component(system_id: str, component_id: str, req: ComponentUpdateRequest):
    profile = catalog_service.update_component(system_id, component_id, req.model_dump(exclude_none=True))
    if not profile:
        raise HTTPException(status_code=404, detail="业务系统画像或组件不存在")
    return ResponseModel(status="success", data={"profile": profile.model_dump(), "summary": profile.summary()})


@router.get("/sources", response_model=ResponseModel)
async def list_observable_sources():
    return ResponseModel(status="success", data={"sources": catalog_service.list_sources()})


@router.get("/discovery-candidates", response_model=ResponseModel)
async def list_observability_discovery_candidates(system_id: str | None = None):
    return ResponseModel(
        status="success",
        data={"candidates": catalog_service.list_discovery_candidates(system_id=system_id)},
    )


@router.get("/investigations", response_model=ResponseModel)
async def list_observability_investigations(system_id: str | None = None):
    return ResponseModel(
        status="success",
        data={"investigations": catalog_service.list_investigations(system_id=system_id)},
    )


@router.post("/investigations", response_model=ResponseModel)
async def create_observability_investigation(req: InvestigationCreateRequest):
    investigation = catalog_service.create_investigation(
        system_id=req.system_id,
        title=req.title,
        symptom=req.symptom,
        time_window=req.time_window,
        severity=req.severity,
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="业务系统画像不存在")
    return ResponseModel(status="success", data={"investigation": investigation.model_dump()})


@router.get("/investigations/{investigation_id}", response_model=ResponseModel)
async def get_observability_investigation(investigation_id: str):
    investigation = catalog_service.get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="排查事件不存在")
    return ResponseModel(status="success", data={"investigation": investigation.model_dump()})


@router.post("/investigations/{investigation_id}/evidence", response_model=ResponseModel)
async def append_observability_evidence(investigation_id: str, req: EvidenceAppendRequest):
    evidence = catalog_service.append_evidence(
        investigation_id,
        title=req.title,
        summary=req.summary,
        evidence_type=req.evidence_type,
        task_id=req.task_id,
        component_id=req.component_id,
        source_id=req.source_id,
        raw_ref=req.raw_ref,
        raw_excerpt=req.raw_excerpt,
        tool_evidence=req.tool_evidence,
        confidence=req.confidence,
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="排查事件不存在")
    investigation = catalog_service.get_investigation(investigation_id)
    return ResponseModel(
        status="success",
        data={"evidence": evidence.model_dump(), "investigation": investigation.model_dump() if investigation else None},
    )


@router.post("/investigations/{investigation_id}/root-causes", response_model=ResponseModel)
async def append_observability_root_cause(investigation_id: str, req: RootCauseAppendRequest):
    candidate = catalog_service.append_root_cause(
        investigation_id,
        title=req.title,
        description=req.description,
        likelihood=req.likelihood,
        impact=req.impact,
        confidence=req.confidence,
        supporting_evidence_ids=req.supporting_evidence_ids,
        recommended_next_steps=req.recommended_next_steps,
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="排查事件不存在")
    investigation = catalog_service.get_investigation(investigation_id)
    return ResponseModel(
        status="success",
        data={"root_cause": candidate.model_dump(), "investigation": investigation.model_dump() if investigation else None},
    )


@router.get("/profile-packs", response_model=ResponseModel)
async def list_observability_profile_packs():
    return ResponseModel(status="success", data={"profile_packs": catalog_service.list_profile_packs()})
