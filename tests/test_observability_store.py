from __future__ import annotations

from pathlib import Path

from core.observability.models import BusinessSystem, Component
from core.observability.store import ObservabilityStore


def store_path(name: str) -> Path:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if path.exists():
        path.unlink()
    return path


def test_store_initialization_is_idempotent():
    path = store_path("observability_store_idempotent.sqlite")
    store = ObservabilityStore(path)
    store.initialize()
    store.initialize()

    system = BusinessSystem(name="集团global协作门户", environment="测试环境")
    saved = store.upsert("systems", system.to_record())

    assert saved["name"] == "集团global协作门户"


def test_store_crud_preserves_json_metadata():
    store = ObservabilityStore(store_path("observability_store_crud.sqlite"))
    system = store.upsert("systems", BusinessSystem(name="系统", environment="测试", tags=["global"]).to_record())
    component = Component(
        system_id=system["id"],
        name="k8s-master",
        component_type="k8s_cluster",
        workload_family="container",
        confidence="confirmed",
        metadata={"labels": {"env": "test"}},
    )

    saved = store.upsert("components", component.to_record())
    loaded = store.get("components", saved["id"])

    assert loaded is not None
    assert loaded["metadata"]["labels"]["env"] == "test"
    assert store.delete("components", saved["id"])

