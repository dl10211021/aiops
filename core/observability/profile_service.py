from __future__ import annotations

from typing import Any

from core.observability.models import BusinessSystem, Component, now_iso
from core.observability.store import ObservabilityStore, get_observability_store


DEFAULT_UNKNOWN_COMPONENTS = [
    ("入口", "business_entry", "application"),
    ("数据库", "unknown", "database"),
    ("网络/交换机", "unknown", "network"),
    ("存储", "unknown", "storage"),
    ("虚拟化/物理平台", "unknown", "infrastructure"),
]


class BusinessSystemProfileService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def create_system(self, **kwargs: Any) -> dict[str, Any]:
        system = BusinessSystem(**kwargs)
        return self.store.upsert("systems", system.to_record())

    def list_systems(self) -> list[dict[str, Any]]:
        systems = self.store.list("systems", order_by="updated_at DESC")
        return [self._with_summary(system) for system in systems]

    def get_system(self, system_id: str) -> dict[str, Any] | None:
        system = self.store.get("systems", system_id)
        return self._with_summary(system) if system else None

    def update_system(self, system_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {
            "name",
            "environment",
            "description",
            "criticality",
            "owner",
            "aliases",
            "tags",
            "status",
            "metadata",
        }
        payload = {key: value for key, value in updates.items() if key in allowed}
        payload["updated_at"] = now_iso()
        updated = self.store.update_fields("systems", system_id, payload)
        return self._with_summary(updated) if updated else None

    def delete_system(self, system_id: str) -> bool:
        for table in ("components", "relationships", "bindings", "source_bindings", "discovery_runs", "review_items", "investigations"):
            self.store.delete_where(table, "system_id = ?", (system_id,))
        return self.store.delete("systems", system_id)

    def bootstrap_partial_profile(
        self,
        *,
        name: str,
        environment: str,
        known_components: list[dict[str, Any]],
        description: str = "",
        criticality: str = "medium",
        owner: str = "",
    ) -> dict[str, Any]:
        system = self.create_system(
            name=name,
            environment=environment,
            description=description,
            criticality=criticality,
            owner=owner,
            status="active",
        )
        for item in known_components:
            component = Component(
                system_id=system["id"],
                name=str(item.get("name") or ""),
                component_type=str(item.get("component_type") or "unknown"),
                workload_family=str(item.get("workload_family") or "application"),
                profile_pack_id=str(item.get("profile_pack_id") or ""),
                environment=str(item.get("environment") or environment),
                status=str(item.get("status") or "known"),
                confidence=str(item.get("confidence") or "confirmed"),
                source=str(item.get("source") or "manual"),
                metadata=dict(item.get("metadata") or {}),
            )
            self.store.upsert("components", component.to_record())
        for label, component_type, family in DEFAULT_UNKNOWN_COMPONENTS:
            component = Component(
                system_id=system["id"],
                name=label,
                component_type=component_type,
                workload_family=family,
                environment=environment,
                status="unknown",
                confidence="unknown",
                source="system_default",
                metadata={"unknown": True},
            )
            self.store.upsert("components", component.to_record())
        return self.get_system(system["id"]) or system

    def calculate_profile_completeness(self, system_id: str) -> int:
        components = self.store.list("components", where="system_id = ?", params=(system_id,))
        relationships = self.store.list("relationships", where="system_id = ?", params=(system_id,))
        bindings = self.store.list("bindings", where="system_id = ?", params=(system_id,))
        source_bindings = self.store.list("source_bindings", where="system_id = ?", params=(system_id,))
        if not components:
            return 0
        known = sum(1 for item in components if item.get("component_type") != "unknown" and item.get("confidence") != "unknown")
        unknown = sum(1 for item in components if item.get("component_type") == "unknown" or item.get("status") == "unknown")
        confirmed_rel = sum(1 for item in relationships if item.get("status") == "confirmed")
        pending_rel = sum(1 for item in relationships if item.get("status") == "pending_review")
        binding_score = min(20, (len(bindings) + len(source_bindings)) * 5)
        topology_score = min(30, confirmed_rel * 5 + pending_rel * 2)
        component_score = int((known / max(1, known + unknown)) * 50)
        return max(0, min(100, component_score + topology_score + binding_score))

    def _with_summary(self, system: dict[str, Any]) -> dict[str, Any]:
        system = dict(system)
        system_id = system["id"]
        components = self.store.list("components", where="system_id = ?", params=(system_id,))
        relationships = self.store.list("relationships", where="system_id = ?", params=(system_id,))
        bindings = self.store.list("bindings", where="system_id = ?", params=(system_id,))
        source_bindings = self.store.list("source_bindings", where="system_id = ?", params=(system_id,))
        completeness = self.calculate_profile_completeness(system_id)
        system["profile_completeness"] = completeness
        system["component_count"] = len(components)
        system["unknown_count"] = sum(1 for item in components if item.get("component_type") == "unknown" or item.get("status") == "unknown")
        system["pending_relationship_count"] = sum(1 for item in relationships if item.get("status") == "pending_review")
        system["bound_asset_count"] = sum(1 for item in bindings if item.get("target_type") == "asset")
        system["bound_session_count"] = sum(1 for item in bindings if item.get("target_type") == "session")
        system["observable_source_count"] = len(source_bindings)
        self.store.update_fields("systems", system_id, {"profile_completeness": completeness})
        return system


def get_profile_service(store: ObservabilityStore | None = None) -> BusinessSystemProfileService:
    return BusinessSystemProfileService(store)
