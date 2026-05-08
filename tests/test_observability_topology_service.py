from __future__ import annotations

from pathlib import Path

from core.observability.profile_service import BusinessSystemProfileService
from core.observability.store import ObservabilityStore
from core.observability.topology_service import TopologyService


def make_store() -> ObservabilityStore:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "observability_topology.sqlite"
    if path.exists():
        path.unlink()
    return ObservabilityStore(path)


def test_layered_topology_is_product_neutral():
    store = make_store()
    system = BusinessSystemProfileService(store).create_system(name="系统", environment="测试")
    topology = TopologyService(store)
    for name, component_type, family in [
        ("ZStack", "cloud_cluster", "virtualization"),
        ("VMware", "cloud_cluster", "virtualization"),
        ("物理机", "physical_server", "physical"),
        ("K8s", "k8s_cluster", "container"),
        ("MySQL", "database_instance", "database"),
        ("Mongo", "database_cluster", "database"),
        ("TiDB", "database_cluster", "distributed_database"),
        ("Oracle", "database_instance", "database"),
        ("Doris", "mpp_cluster", "mpp_database"),
        ("Hadoop", "bigdata_cluster", "bigdata"),
        ("交换机", "network_switch", "network"),
        ("EDR", "security_tool", "security"),
    ]:
        topology.create_component(system["id"], {"name": name, "component_type": component_type, "workload_family": family, "confidence": "confirmed"})
    topology.create_unknown_node(system["id"], "未知 OS", "os")

    result = topology.layered_topology(system["id"])
    layers = {layer["id"]: layer for layer in result["layers"]}

    assert len(layers["virtualization"]["nodes"]) == 2
    assert layers["database"]["nodes"]
    assert layers["bigdata"]["nodes"]
    assert layers["mpp"]["nodes"]
    assert layers["unknown"]["nodes"]

