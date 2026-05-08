from __future__ import annotations

import json
from pathlib import Path
import uuid

import pytest

from core.observability.agent_orchestrator import ObservabilityAgentOrchestrator
from core.observability.binding_service import BindingService
from core.observability.evidence_service import EvidenceService
from core.observability.investigation_service import InvestigationService
from core.observability.profile_service import BusinessSystemProfileService
from core.observability.store import ObservabilityStore
from core.observability.topology_service import TopologyService


def make_store() -> ObservabilityStore:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"observability_investigation_{uuid.uuid4().hex}.sqlite"
    return ObservabilityStore(path)


def test_create_investigation_plan_evidence_and_root_cause():
    store = make_store()
    system = BusinessSystemProfileService(store).create_system(name="集团global协作门户", environment="测试环境")
    component = TopologyService(store).create_component(system["id"], {"name": "k8s", "component_type": "k8s_cluster", "workload_family": "container", "confidence": "confirmed"})
    service = InvestigationService(store)
    investigation = service.create_investigation({"system_id": system["id"], "title": "系统慢", "symptom": "系统慢"})
    tasks = service.build_plan(investigation["id"])

    assert tasks
    evidence = EvidenceService(store).append_evidence(
        {
            "investigation_id": investigation["id"],
            "component_id": component["id"],
            "evidence_type": "metric",
            "title": "CPU 使用率升高",
            "summary": "node exporter 显示 CPU 使用率升高",
            "confidence": "discovered",
        }
    )
    root_cause = EvidenceService(store).append_root_cause_candidate(
        {
            "investigation_id": investigation["id"],
            "title": "节点 CPU 饱和",
            "description": "慢请求时间窗内 CPU 饱和。",
            "supporting_evidence_ids": [evidence["id"]],
            "likelihood": 70,
            "confidence": "inferred",
        }
    )

    detail = service.get_investigation(investigation["id"])
    assert detail["evidence_count"] == 1
    assert root_cause["supporting_evidence_ids"] == [evidence["id"]]


def test_existing_alert_inspection_canvas_can_attach_as_evidence():
    store = make_store()
    system = BusinessSystemProfileService(store).create_system(name="系统", environment="测试")
    investigation = InvestigationService(store).create_investigation({"system_id": system["id"], "title": "系统慢", "symptom": "系统慢"})
    evidence = EvidenceService(store)

    evidence.attach_alert_event(investigation["id"], {"id": "alert-1", "alert_name": "HighCPU", "description": "CPU 高"})
    evidence.attach_inspection_result(investigation["id"], {"run_id": "run-1", "summary": "巡检发现 IO 等待升高"})
    evidence.attach_canvas_reference(investigation["id"], {"id": "canvas-1", "title": "慢请求画板"})

    rows = evidence.list_evidence(investigation["id"])
    assert {row["evidence_type"] for row in rows} == {"alert", "inspection", "canvas"}


@pytest.mark.asyncio
async def test_orchestrator_creates_tasks_and_captures_stubbed_dispatch():
    store = make_store()
    system = BusinessSystemProfileService(store).create_system(name="集团global协作门户", environment="测试环境")
    component = TopologyService(store).create_component(system["id"], {"name": "k8s", "component_type": "k8s_cluster", "workload_family": "container", "confidence": "confirmed"})
    BindingService(store).bind_component_session(system["id"], component["id"], "globa-session-1")
    investigation = InvestigationService(store).create_investigation({"system_id": system["id"], "title": "系统慢", "symptom": "系统慢"})

    async def fake_dispatch(tasks, allow_modifications):
        assert allow_modifications is False
        assert tasks[0]["target_session_id"] == "globa-session-1"
        return {"ok": True, "tasks": tasks}

    result = await ObservabilityAgentOrchestrator(store, fake_dispatch).dispatch_investigation_tasks(investigation["id"])
    detail = InvestigationService(store).get_investigation(investigation["id"])

    assert result["status"] == "completed"
    assert detail["evidence_count"] >= 1
    assert "只读" in json.dumps(detail["tasks"], ensure_ascii=False)
