from __future__ import annotations

from typing import Any

from core.observability.models import Component, LAYER_ORDER, Relationship, relationship_endpoints_are_valid
from core.observability.store import ObservabilityStore, get_observability_store


LAYER_LABELS = {
    "business": "业务系统层",
    "entry": "入口层",
    "app": "应用层",
    "container": "容器/K8s层",
    "os": "操作系统层",
    "virtualization": "虚拟化/云平台层",
    "physical": "物理基础设施层",
    "network": "网络层",
    "database": "数据库层",
    "bigdata": "大数据层",
    "mpp": "MPP层",
    "middleware": "中间件层",
    "security": "观测/安全层",
    "observability": "观测源层",
    "unknown": "未知层",
}


class TopologyService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def create_component(self, system_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        component = Component(system_id=system_id, **payload)
        return self.store.upsert("components", component.to_record())

    def list_components(self, system_id: str) -> list[dict[str, Any]]:
        return self.store.list("components", where="system_id = ?", params=(system_id,), order_by="created_at ASC")

    def update_component(self, system_id: str, component_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        current = self.store.get("components", component_id)
        if not current or current.get("system_id") != system_id:
            return None
        allowed = {"name", "component_type", "workload_family", "profile_pack_id", "environment", "status", "confidence", "source", "metadata"}
        return self.store.update_fields("components", component_id, {k: v for k, v in payload.items() if k in allowed})

    def delete_component(self, system_id: str, component_id: str) -> bool:
        current = self.store.get("components", component_id)
        if not current or current.get("system_id") != system_id:
            return False
        self.store.delete_where("relationships", "system_id = ? AND (from_component_id = ? OR to_component_id = ?)", (system_id, component_id, component_id))
        self.store.delete_where("bindings", "system_id = ? AND component_id = ?", (system_id, component_id))
        return self.store.delete("components", component_id)

    def create_relationship(self, system_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        relationship = Relationship(system_id=system_id, **payload)
        components = self.list_components(system_id)
        if not relationship_endpoints_are_valid(relationship, components):
            raise ValueError("relationship endpoints must belong to the system")
        return self.store.upsert("relationships", relationship.to_record())

    def list_relationships(self, system_id: str) -> list[dict[str, Any]]:
        return self.store.list("relationships", where="system_id = ?", params=(system_id,), order_by="created_at ASC")

    def update_relationship(self, system_id: str, relationship_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        current = self.store.get("relationships", relationship_id)
        if not current or current.get("system_id") != system_id:
            return None
        allowed = {"relationship_type", "confidence", "source", "evidence_id", "status", "metadata"}
        return self.store.update_fields("relationships", relationship_id, {k: v for k, v in payload.items() if k in allowed})

    def delete_relationship(self, system_id: str, relationship_id: str) -> bool:
        current = self.store.get("relationships", relationship_id)
        if not current or current.get("system_id") != system_id:
            return False
        return self.store.delete("relationships", relationship_id)

    def create_unknown_node(self, system_id: str, name: str, workload_family: str) -> dict[str, Any]:
        return self.create_component(
            system_id,
            {
                "name": name,
                "component_type": "unknown",
                "workload_family": workload_family,
                "status": "unknown",
                "confidence": "unknown",
                "source": "manual_unknown",
                "metadata": {"unknown": True},
            },
        )

    def layered_topology(self, system_id: str) -> dict[str, Any]:
        components = self.list_components(system_id)
        relationships = self.list_relationships(system_id)
        bindings = self.store.list("bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC")
        source_bindings = self.store.list("source_bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC")
        binding_counts: dict[str, dict[str, int]] = {}
        for item in bindings:
            component_id = item.get("component_id") or ""
            bucket = binding_counts.setdefault(component_id, {"assets": 0, "sessions": 0, "sources": 0})
            if item.get("target_type") == "asset":
                bucket["assets"] += 1
            if item.get("target_type") == "session":
                bucket["sessions"] += 1
        for item in source_bindings:
            component_id = item.get("component_id") or ""
            if not component_id:
                continue
            binding_counts.setdefault(component_id, {"assets": 0, "sessions": 0, "sources": 0})["sources"] += 1

        layers = []
        for layer_id in LAYER_ORDER:
            nodes = []
            for component in components:
                enriched = dict(component)
                enriched["layer"] = Component(
                    system_id=component["system_id"],
                    id=component["id"],
                    name=component["name"],
                    component_type=component["component_type"],
                    workload_family=component.get("workload_family") or "unknown",
                ).layer
                if enriched["layer"] != layer_id:
                    continue
                counts = binding_counts.get(enriched["id"], {"assets": 0, "sessions": 0, "sources": 0})
                enriched["bound_asset_count"] = counts["assets"]
                enriched["bound_session_count"] = counts["sessions"]
                enriched["bound_source_count"] = counts["sources"]
                nodes.append(enriched)
            layers.append({"id": layer_id, "label": LAYER_LABELS[layer_id], "nodes": nodes})
        return {"system_id": system_id, "layers": layers, "relationships": relationships}


def get_topology_service(store: ObservabilityStore | None = None) -> TopologyService:
    return TopologyService(store)
