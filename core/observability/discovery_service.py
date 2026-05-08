from __future__ import annotations

from typing import Any

from core.observability.models import Relationship, new_id, now_iso
from core.observability.store import ObservabilityStore, get_observability_store
from core.observability.topology_service import TopologyService


class DiscoveryService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()
        self.topology = TopologyService(self.store)

    def create_discovery_run(self, system_id: str, input_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        now = now_iso()
        run = {
            "id": new_id("obs_disc"),
            "system_id": system_id,
            "status": "completed",
            "input": input_payload or {},
            "summary": {},
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        self.store.upsert("discovery_runs", run)
        proposals = self._generate_relationship_proposals(run["id"], system_id, input_payload or {})
        run["summary"] = {"proposal_count": len(proposals)}
        return self.store.upsert("discovery_runs", run)

    def get_discovery_run(self, run_id: str) -> dict[str, Any] | None:
        run = self.store.get("discovery_runs", run_id)
        if not run:
            return None
        run["review_items"] = self.store.list("review_items", where="run_id = ?", params=(run_id,), order_by="created_at ASC")
        return run

    def confirm_review_item(self, item_id: str) -> dict[str, Any] | None:
        item = self.store.get("review_items", item_id)
        if not item:
            return None
        relationship = Relationship(
            system_id=item["system_id"],
            from_component_id=item["from_component_id"],
            to_component_id=item["to_component_id"],
            relationship_type=item["relationship_type"],
            confidence=item.get("confidence") or "inferred",
            source="discovery_review",
            status="confirmed",
            metadata={"review_item_id": item_id},
        )
        payload = relationship.to_record()
        payload.pop("system_id", None)
        created = self.topology.create_relationship(item["system_id"], payload)
        self.store.update_fields("review_items", item_id, {"status": "confirmed", "metadata": {"created_relationship_id": created["id"]}})
        return self.store.get("review_items", item_id)

    def reject_review_item(self, item_id: str) -> dict[str, Any] | None:
        return self.store.update_fields("review_items", item_id, {"status": "rejected"})

    def _generate_relationship_proposals(self, run_id: str, system_id: str, input_payload: dict[str, Any]) -> list[dict[str, Any]]:
        components = self.topology.list_components(system_id)
        proposals: list[dict[str, Any]] = []
        registries = [item for item in components if item.get("component_type") == "container_registry"]
        k8s_nodes = [item for item in components if item.get("component_type") in {"k8s_cluster", "k8s_workload", "k8s_service"}]
        middleware = [item for item in components if item.get("component_type") == "middleware"]
        for source in registries:
            for target in k8s_nodes[:2]:
                proposals.append(self._review_item(run_id, system_id, source["id"], target["id"], "pulls_image_from", "k8s/registry naming hints"))
        for source in middleware[:1]:
            for target in k8s_nodes[:1]:
                proposals.append(self._review_item(run_id, system_id, target["id"], source["id"], "uses_middleware", "middleware component supplied by user"))
        for item in input_payload.get("relationships", []) if isinstance(input_payload.get("relationships"), list) else []:
            proposals.append(
                self._review_item(
                    run_id,
                    system_id,
                    str(item.get("from_component_id") or ""),
                    str(item.get("to_component_id") or ""),
                    str(item.get("relationship_type") or "depends_on"),
                    "user supplied discovery input",
                )
            )
        return [self.store.upsert("review_items", item) for item in proposals if item["from_component_id"] and item["to_component_id"]]

    def _review_item(self, run_id: str, system_id: str, from_id: str, to_id: str, rel_type: str, evidence: str) -> dict[str, Any]:
        now = now_iso()
        return {
            "id": new_id("obs_review"),
            "run_id": run_id,
            "system_id": system_id,
            "candidate_type": "relationship",
            "from_component_id": from_id,
            "to_component_id": to_id,
            "relationship_type": rel_type,
            "confidence": "inferred",
            "status": "pending_review",
            "evidence": [{"summary": evidence, "source": "rule"}],
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }


def get_discovery_service(store: ObservabilityStore | None = None) -> DiscoveryService:
    return DiscoveryService(store)
