from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schema_models.common import ResponseModel
from core.observability.agent_orchestrator import ObservabilityAgentOrchestrator
from core.observability.binding_service import get_binding_service
from core.observability.discovery_service import get_discovery_service
from core.observability.evidence_service import get_evidence_service
from core.observability.investigation_service import get_investigation_service
from core.observability.profile_pack_service import get_profile_pack_service
from core.observability.profile_service import get_profile_service
from core.observability.source_registry import get_source_registry
from core.observability.topology_service import get_topology_service


router = APIRouter(prefix="/observability")


def ok(data: dict | list | None = None, message: str = "") -> ResponseModel:
    return ResponseModel(status="success", data={"items": data} if isinstance(data, list) else (data or {}), message=message)


def _handle_error(exc: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def _not_found(message: str) -> None:
    raise HTTPException(status_code=404, detail=message)


@router.get("/systems", response_model=ResponseModel)
async def list_systems():
    return ok({"systems": get_profile_service().list_systems()})


@router.post("/systems", response_model=ResponseModel)
async def create_system(payload: dict):
    try:
        if payload.get("known_components"):
            system = get_profile_service().bootstrap_partial_profile(
                name=payload.get("name") or "",
                environment=payload.get("environment") or "",
                known_components=payload.get("known_components") or [],
                description=payload.get("description") or "",
                criticality=payload.get("criticality") or "medium",
                owner=payload.get("owner") or "",
            )
        else:
            system = get_profile_service().create_system(**payload)
        return ok({"system": system})
    except Exception as exc:
        _handle_error(exc)


@router.get("/systems/{system_id}", response_model=ResponseModel)
async def get_system(system_id: str):
    system = get_profile_service().get_system(system_id)
    if not system:
        _not_found("business system not found")
    return ok({"system": system})


@router.put("/systems/{system_id}", response_model=ResponseModel)
async def update_system(system_id: str, payload: dict):
    system = get_profile_service().update_system(system_id, payload)
    if not system:
        _not_found("business system not found")
    return ok({"system": system})


@router.delete("/systems/{system_id}", response_model=ResponseModel)
async def delete_system(system_id: str):
    return ok({"deleted": get_profile_service().delete_system(system_id)})


@router.get("/systems/{system_id}/components", response_model=ResponseModel)
async def list_components(system_id: str):
    return ok({"components": get_topology_service().list_components(system_id)})


@router.post("/systems/{system_id}/components", response_model=ResponseModel)
async def create_component(system_id: str, payload: dict):
    try:
        return ok({"component": get_topology_service().create_component(system_id, payload)})
    except Exception as exc:
        _handle_error(exc)


@router.put("/systems/{system_id}/components/{component_id}", response_model=ResponseModel)
async def update_component(system_id: str, component_id: str, payload: dict):
    component = get_topology_service().update_component(system_id, component_id, payload)
    if not component:
        _not_found("component not found")
    return ok({"component": component})


@router.delete("/systems/{system_id}/components/{component_id}", response_model=ResponseModel)
async def delete_component(system_id: str, component_id: str):
    return ok({"deleted": get_topology_service().delete_component(system_id, component_id)})


@router.get("/systems/{system_id}/relationships", response_model=ResponseModel)
async def list_relationships(system_id: str):
    return ok({"relationships": get_topology_service().list_relationships(system_id)})


@router.post("/systems/{system_id}/relationships", response_model=ResponseModel)
async def create_relationship(system_id: str, payload: dict):
    try:
        return ok({"relationship": get_topology_service().create_relationship(system_id, payload)})
    except Exception as exc:
        _handle_error(exc)


@router.put("/systems/{system_id}/relationships/{relationship_id}", response_model=ResponseModel)
async def update_relationship(system_id: str, relationship_id: str, payload: dict):
    relationship = get_topology_service().update_relationship(system_id, relationship_id, payload)
    if not relationship:
        _not_found("relationship not found")
    return ok({"relationship": relationship})


@router.delete("/systems/{system_id}/relationships/{relationship_id}", response_model=ResponseModel)
async def delete_relationship(system_id: str, relationship_id: str):
    return ok({"deleted": get_topology_service().delete_relationship(system_id, relationship_id)})


@router.get("/systems/{system_id}/topology", response_model=ResponseModel)
async def get_topology(system_id: str):
    return ok({"topology": get_topology_service().layered_topology(system_id)})


@router.get("/systems/{system_id}/bindings", response_model=ResponseModel)
async def list_bindings(system_id: str):
    return ok({"bindings": get_binding_service().list_bindings(system_id)})


@router.post("/systems/{system_id}/bindings/assets", response_model=ResponseModel)
async def bind_asset(system_id: str, payload: dict):
    return ok({"binding": get_binding_service().bind_asset(system_id, payload.get("component_id") or "", str(payload.get("asset_id") or ""), payload.get("metadata") or {})})


@router.post("/systems/{system_id}/bindings/sessions", response_model=ResponseModel)
async def bind_session(system_id: str, payload: dict):
    component_id = payload.get("component_id") or ""
    service = get_binding_service()
    binding = service.bind_component_session(system_id, component_id, str(payload.get("session_id") or ""), payload.get("metadata") or {}) if component_id else service.bind_system_session(system_id, str(payload.get("session_id") or ""), payload.get("metadata") or {})
    return ok({"binding": binding})


@router.get("/sources", response_model=ResponseModel)
async def list_sources():
    return ok({"sources": get_source_registry().list_sources()})


@router.post("/sources", response_model=ResponseModel)
async def create_source(payload: dict):
    try:
        return ok({"source": get_source_registry().create_source(payload)})
    except Exception as exc:
        _handle_error(exc)


@router.post("/sources/from-session", response_model=ResponseModel)
async def create_source_from_session(payload: dict):
    try:
        source = get_source_registry().create_source_from_session(
            session_id=str(payload.get("session_id") or ""),
            source_type=str(payload.get("source_type") or "prometheus"),
            name=payload.get("name"),
            capabilities=payload.get("capabilities"),
            endpoint=str(payload.get("endpoint") or ""),
            metadata=payload.get("metadata") or {},
        )
        system_id = str(payload.get("system_id") or "")
        component_id = str(payload.get("component_id") or "")
        if system_id or component_id:
            get_source_registry().bind_source(source["id"], system_id, component_id)
        return ok({"source": source})
    except Exception as exc:
        _handle_error(exc)


@router.get("/sources/{source_id}", response_model=ResponseModel)
async def get_source(source_id: str):
    source = get_source_registry().get_source(source_id)
    if not source:
        _not_found("source not found")
    return ok({"source": source})


@router.put("/sources/{source_id}", response_model=ResponseModel)
async def update_source(source_id: str, payload: dict):
    source = get_source_registry().update_source(source_id, payload)
    if not source:
        _not_found("source not found")
    return ok({"source": source})


@router.post("/sources/{source_id}/check", response_model=ResponseModel)
async def check_source(source_id: str):
    source = get_source_registry().check_source(source_id)
    if not source:
        _not_found("source not found")
    return ok({"source": source})


@router.get("/profile-packs", response_model=ResponseModel)
async def list_profile_packs():
    return ok({"profile_packs": get_profile_pack_service().list_packs()})


@router.get("/profile-packs/{pack_id}", response_model=ResponseModel)
async def get_profile_pack(pack_id: str):
    pack = get_profile_pack_service().get_pack(pack_id)
    if not pack:
        _not_found("profile pack not found")
    return ok({"profile_pack": pack})


@router.post("/systems/{system_id}/discovery-runs", response_model=ResponseModel)
async def create_discovery_run(system_id: str, payload: dict | None = None):
    return ok({"run": get_discovery_service().create_discovery_run(system_id, payload or {})})


@router.get("/discovery-runs/{run_id}", response_model=ResponseModel)
async def get_discovery_run(run_id: str):
    run = get_discovery_service().get_discovery_run(run_id)
    if not run:
        _not_found("discovery run not found")
    return ok({"run": run})


@router.post("/relationship-review-items/{item_id}/confirm", response_model=ResponseModel)
async def confirm_review_item(item_id: str):
    item = get_discovery_service().confirm_review_item(item_id)
    if not item:
        _not_found("review item not found")
    return ok({"review_item": item})


@router.post("/relationship-review-items/{item_id}/reject", response_model=ResponseModel)
async def reject_review_item(item_id: str):
    item = get_discovery_service().reject_review_item(item_id)
    if not item:
        _not_found("review item not found")
    return ok({"review_item": item})


@router.get("/investigations", response_model=ResponseModel)
async def list_investigations():
    return ok({"investigations": get_investigation_service().list_investigations()})


@router.post("/investigations", response_model=ResponseModel)
async def create_investigation(payload: dict):
    try:
        return ok({"investigation": get_investigation_service().create_investigation(payload)})
    except Exception as exc:
        _handle_error(exc)


@router.get("/investigations/{investigation_id}", response_model=ResponseModel)
async def get_investigation(investigation_id: str):
    investigation = get_investigation_service().get_investigation(investigation_id)
    if not investigation:
        _not_found("investigation not found")
    return ok({"investigation": investigation})


@router.post("/investigations/{investigation_id}/plan", response_model=ResponseModel)
async def plan_investigation(investigation_id: str):
    return ok({"tasks": get_investigation_service().build_plan(investigation_id)})


@router.post("/investigations/{investigation_id}/dispatch", response_model=ResponseModel)
async def dispatch_investigation(investigation_id: str):
    result = await ObservabilityAgentOrchestrator().dispatch_investigation_tasks(investigation_id)
    return ok({"dispatch": result})


@router.get("/investigations/{investigation_id}/evidence", response_model=ResponseModel)
async def list_evidence(investigation_id: str):
    return ok({"evidence": get_evidence_service().list_evidence(investigation_id)})


@router.post("/investigations/{investigation_id}/evidence", response_model=ResponseModel)
async def append_evidence(investigation_id: str, payload: dict):
    return ok({"evidence": get_evidence_service().append_evidence({**payload, "investigation_id": investigation_id})})


@router.post("/investigations/{investigation_id}/evidence/alerts", response_model=ResponseModel)
async def attach_alert_evidence(investigation_id: str, payload: dict):
    return ok({"evidence": get_evidence_service().attach_alert_event(investigation_id, payload)})


@router.post("/investigations/{investigation_id}/evidence/inspection-results", response_model=ResponseModel)
async def attach_inspection_evidence(investigation_id: str, payload: dict):
    return ok({"evidence": get_evidence_service().attach_inspection_result(investigation_id, payload)})


@router.post("/investigations/{investigation_id}/evidence/canvas-references", response_model=ResponseModel)
async def attach_canvas_evidence(investigation_id: str, payload: dict):
    return ok({"evidence": get_evidence_service().attach_canvas_reference(investigation_id, payload)})


@router.get("/investigations/{investigation_id}/root-causes", response_model=ResponseModel)
async def list_root_causes(investigation_id: str):
    return ok({"root_causes": get_evidence_service().list_root_causes(investigation_id)})


@router.post("/investigations/{investigation_id}/root-causes", response_model=ResponseModel)
async def append_root_cause(investigation_id: str, payload: dict):
    return ok({"root_cause": get_evidence_service().append_root_cause_candidate({**payload, "investigation_id": investigation_id})})
