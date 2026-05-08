from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability_routes import router
from core.observability.store import ObservabilityStore, set_observability_store


def client() -> TestClient:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"observability_routes_{uuid.uuid4().hex}.sqlite"
    set_observability_store(ObservabilityStore(path))
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_observability_routes_cover_system_source_investigation_flow():
    c = client()
    created = c.post(
        "/api/v1/observability/systems",
        json={
            "name": "集团global协作门户",
            "environment": "测试环境",
            "known_components": [
                {"name": "registry", "component_type": "container_registry", "workload_family": "container"},
                {"name": "k8s-master", "component_type": "k8s_cluster", "workload_family": "container"},
                {"name": "中间件服务器", "component_type": "middleware", "workload_family": "middleware"},
            ],
        },
    )
    assert created.status_code == 200
    system = created.json()["data"]["system"]

    systems = c.get("/api/v1/observability/systems").json()["data"]["systems"]
    assert systems[0]["unknown_count"] >= 1

    source = c.post(
        "/api/v1/observability/sources/from-session",
        json={"session_id": "prometheus-session", "source_type": "prometheus", "system_id": system["id"]},
    )
    assert source.status_code == 200
    assert "query_promql" in source.json()["data"]["source"]["capabilities"]

    investigation = c.post(
        "/api/v1/observability/investigations",
        json={"system_id": system["id"], "title": "系统慢", "symptom": "系统慢"},
    ).json()["data"]["investigation"]
    plan = c.post(f"/api/v1/observability/investigations/{investigation['id']}/plan")
    assert plan.status_code == 200
    assert plan.json()["data"]["tasks"]


def test_relationship_endpoint_validation_returns_400():
    c = client()
    system = c.post("/api/v1/observability/systems", json={"name": "系统", "environment": "测试"}).json()["data"]["system"]
    response = c.post(
        f"/api/v1/observability/systems/{system['id']}/relationships",
        json={
            "from_component_id": "missing-a",
            "to_component_id": "missing-b",
            "relationship_type": "depends_on",
        },
    )
    assert response.status_code == 400
