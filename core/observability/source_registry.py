from __future__ import annotations

from typing import Any

from core.observability.models import ObservableSource, new_id, now_iso
from core.observability.store import ObservabilityStore, get_observability_store


PROMETHEUS_CAPABILITIES = [
    "query_metrics",
    "query_alerts",
    "discover_targets",
    "query_promql",
    "map_exporter_to_component",
]

SOURCE_DEFAULTS = {
    "prometheus": PROMETHEUS_CAPABILITIES,
    "snmp": ["run_readonly_check"],
    "vmware_vcenter": ["discover_topology", "run_readonly_check"],
    "zstack": ["discover_topology", "run_readonly_check"],
    "elk": ["query_logs"],
    "edr": ["query_security_events"],
    "ndr": ["query_network_flows"],
    "database_connection": ["run_readonly_check"],
}


class SourceRegistry:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def create_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_type = str(payload.get("source_type") or "")
        capabilities = payload.get("capabilities") or SOURCE_DEFAULTS.get(source_type, [])
        source = ObservableSource(**{**payload, "capabilities": capabilities})
        return self.store.upsert("sources", source.to_record())

    def create_source_from_session(
        self,
        *,
        session_id: str,
        source_type: str,
        name: str | None = None,
        capabilities: list[str] | None = None,
        endpoint: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.create_source(
            {
                "name": name or f"{source_type} session {session_id}",
                "source_type": source_type,
                "source_origin": "session",
                "session_id": session_id,
                "endpoint": endpoint,
                "capabilities": capabilities or SOURCE_DEFAULTS.get(source_type, []),
                "status": "registered",
                "metadata": metadata or {},
            }
        )

    def list_sources(self) -> list[dict[str, Any]]:
        return self.store.list("sources", order_by="updated_at DESC")

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return self.store.get("sources", source_id)

    def update_source(self, source_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"name", "source_type", "source_origin", "session_id", "endpoint", "capabilities", "auth_ref", "status", "last_checked_at", "metadata"}
        return self.store.update_fields("sources", source_id, {key: value for key, value in payload.items() if key in allowed})

    def bind_source(self, source_id: str, system_id: str = "", component_id: str = "") -> dict[str, Any]:
        now = now_iso()
        record = {
            "id": new_id("obs_src_bind"),
            "source_id": source_id,
            "system_id": system_id,
            "component_id": component_id,
            "created_at": now,
        }
        return self.store.upsert("source_bindings", record)

    def list_source_bindings(self, source_id: str | None = None, system_id: str | None = None) -> list[dict[str, Any]]:
        if source_id:
            return self.store.list("source_bindings", where="source_id = ?", params=(source_id,), order_by="created_at ASC")
        if system_id:
            return self.store.list("source_bindings", where="system_id = ?", params=(system_id,), order_by="created_at ASC")
        return self.store.list("source_bindings", order_by="created_at ASC")

    def check_source(self, source_id: str) -> dict[str, Any] | None:
        source = self.get_source(source_id)
        if not source:
            return None
        return self.update_source(source_id, {"status": "registered", "last_checked_at": now_iso()})


def get_source_registry(store: ObservabilityStore | None = None) -> SourceRegistry:
    return SourceRegistry(store)

