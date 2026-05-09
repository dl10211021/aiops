from __future__ import annotations

from pathlib import Path

from core.observability.discovery_service import DiscoveryService
from core.observability.profile_service import BusinessSystemProfileService
from core.observability.store import ObservabilityStore
from core.observability.topology_service import TopologyService


def make_store(name: str) -> ObservabilityStore:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if path.exists():
        path.unlink()
    return ObservabilityStore(path)


def global_components():
    return [
        {"name": "registry 测试环境", "component_type": "container_registry", "workload_family": "container"},
        {"name": "k8s-master 测试环境", "component_type": "k8s_cluster", "workload_family": "container"},
        {"name": "k8s-worker-1 测试环境", "component_type": "os_host", "workload_family": "os"},
        {"name": "k8s-worker-2 测试环境", "component_type": "os_host", "workload_family": "os"},
        {"name": "中间件服务器 测试环境", "component_type": "middleware", "workload_family": "middleware"},
    ]


def test_bootstrap_global_partial_profile_with_unknown_nodes():
    store = make_store("observability_profile.sqlite")
    service = BusinessSystemProfileService(store)

    system = service.bootstrap_partial_profile(
        name="集团global协作门户",
        environment="测试环境",
        known_components=global_components(),
    )

    assert system["component_count"] >= 10
    assert system["unknown_count"] >= 4
    assert 0 < system["profile_completeness"] < 100


def test_discovery_proposals_require_manual_confirmation():
    store = make_store("observability_discovery.sqlite")
    profile = BusinessSystemProfileService(store)
    topology = TopologyService(store)
    discovery = DiscoveryService(store)
    system = profile.bootstrap_partial_profile(
        name="集团global协作门户",
        environment="测试环境",
        known_components=global_components(),
    )

    run = discovery.create_discovery_run(system["id"])
    run = discovery.get_discovery_run(run["id"])

    assert run is not None
    assert run["review_items"]
    assert topology.list_relationships(system["id"]) == []
    confirmed = discovery.confirm_review_item(run["review_items"][0]["id"])
    assert confirmed["status"] == "confirmed"
    assert topology.list_relationships(system["id"])[0]["status"] == "confirmed"
