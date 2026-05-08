from __future__ import annotations

from pathlib import Path

from core.observability.binding_service import BindingService
from core.observability.profile_service import BusinessSystemProfileService
from core.observability.source_registry import SourceRegistry
from core.observability.store import ObservabilityStore
from core.observability.topology_service import TopologyService


def make_store() -> ObservabilityStore:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "observability_bindings.sqlite"
    if path.exists():
        path.unlink()
    return ObservabilityStore(path)


def test_bind_components_to_assets_sessions_and_prometheus_source():
    store = make_store()
    system = BusinessSystemProfileService(store).create_system(name="集团global协作门户", environment="测试环境")
    topology = TopologyService(store)
    registry = topology.create_component(system["id"], {"name": "registry", "component_type": "container_registry", "workload_family": "container", "confidence": "confirmed"})
    k8s = topology.create_component(system["id"], {"name": "k8s-master", "component_type": "k8s_cluster", "workload_family": "container", "confidence": "confirmed"})
    middleware = topology.create_component(system["id"], {"name": "中间件服务器", "component_type": "middleware", "workload_family": "middleware", "confidence": "confirmed"})
    bindings = BindingService(store)

    bindings.bind_asset(system["id"], registry["id"], "asset-registry")
    bindings.bind_component_session(system["id"], k8s["id"], "session-k8s")
    bindings.bind_component_session(system["id"], middleware["id"], "session-middleware")
    source = SourceRegistry(store).create_source_from_session(session_id="session-prometheus", source_type="prometheus", name="Prometheus 会话")
    SourceRegistry(store).bind_source(source["id"], system["id"], k8s["id"])

    persisted = BindingService(ObservabilityStore(store.db_path)).list_bindings(system["id"])

    assert len(persisted) == 3
    assert any(item["relation_type"] == "queried_through_session" for item in persisted)
    assert source["capabilities"] == ["query_metrics", "query_alerts", "discover_targets", "query_promql", "map_exporter_to_component"]

