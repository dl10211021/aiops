from __future__ import annotations

from typing import Any

from core.observability.models import new_id, now_iso
from core.observability.store import ObservabilityStore, get_observability_store


class BindingService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def bind_asset(self, system_id: str, component_id: str, asset_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._bind(system_id, component_id, "asset", asset_id, "bound_asset", metadata)

    def bind_component_session(self, system_id: str, component_id: str, session_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._bind(system_id, component_id, "session", session_id, "queried_through_session", metadata)

    def bind_system_session(self, system_id: str, session_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._bind(system_id, "", "session", session_id, "queried_through_session", metadata)

    def list_bindings(self, system_id: str) -> list[dict[str, Any]]:
        return self.store.list("bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC")

    def _bind(
        self,
        system_id: str,
        component_id: str,
        target_type: str,
        target_id: str,
        relation_type: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now = now_iso()
        record = {
            "id": new_id("obs_bind"),
            "system_id": system_id,
            "component_id": component_id,
            "target_type": target_type,
            "target_id": str(target_id),
            "relation_type": relation_type,
            "source_id": "",
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        return self.store.upsert("bindings", record)


def get_binding_service(store: ObservabilityStore | None = None) -> BindingService:
    return BindingService(store)

