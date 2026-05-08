from __future__ import annotations

from typing import Any

from core.observability.evidence_service import EvidenceService
from core.observability.models import Investigation, InvestigationTask, now_iso
from core.observability.profile_pack_service import ProfilePackService
from core.observability.store import ObservabilityStore, get_observability_store
from core.observability.topology_service import TopologyService


ROLE_BY_LAYER = {
    "observability": "Prometheus Agent",
    "os": "OS Agent",
    "container": "K8s Agent",
    "database": "Database Agent",
    "middleware": "Middleware Agent",
    "network": "Network Agent",
    "security": "Security Agent",
}


class InvestigationService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()
        self.topology = TopologyService(self.store)
        self.evidence = EvidenceService(self.store)
        self.packs = ProfilePackService(self.store)

    def create_investigation(self, payload: dict[str, Any]) -> dict[str, Any]:
        investigation = Investigation(**payload)
        return self.store.upsert("investigations", investigation.to_record())

    def list_investigations(self) -> list[dict[str, Any]]:
        items = self.store.list("investigations", order_by="created_at DESC")
        return [self._with_counts(item) for item in items]

    def get_investigation(self, investigation_id: str) -> dict[str, Any] | None:
        item = self.store.get("investigations", investigation_id)
        if not item:
            return None
        item = self._with_counts(item)
        item["tasks"] = self.list_tasks(investigation_id)
        item["evidence"] = self.evidence.list_evidence(investigation_id)
        item["root_causes"] = self.evidence.list_root_causes(investigation_id)
        return item

    def list_tasks(self, investigation_id: str) -> list[dict[str, Any]]:
        return self.store.list("tasks", where="investigation_id = ?", params=(investigation_id,), order_by="created_at ASC")

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = InvestigationTask(**payload)
        return self.store.upsert("tasks", task.to_record())

    def build_plan(self, investigation_id: str) -> list[dict[str, Any]]:
        investigation = self.store.get("investigations", investigation_id)
        if not investigation:
            raise ValueError("investigation not found")
        topology = self.topology.layered_topology(investigation["system_id"])
        existing = self.list_tasks(investigation_id)
        if existing:
            return existing
        tasks: list[dict[str, Any]] = []
        for layer in topology["layers"]:
            role = ROLE_BY_LAYER.get(layer["id"])
            if not role or not layer["nodes"]:
                continue
            for node in layer["nodes"][:3]:
                tasks.append(
                    self.create_task(
                        {
                            "investigation_id": investigation_id,
                            "agent_role": role,
                            "target_component_id": node["id"],
                            "task_type": "readonly_investigation",
                            "status": "pending",
                            "input": {
                                "symptom": investigation.get("symptom"),
                                "component": node,
                                "readonly": True,
                                "mode_label": "只读排查",
                            },
                        }
                    )
                )
        if not tasks:
            tasks.append(
                self.create_task(
                    {
                        "investigation_id": investigation_id,
                        "agent_role": "Summary Agent",
                        "task_type": "profile_gap_summary",
                        "status": "pending",
                        "input": {"symptom": investigation.get("symptom"), "readonly": True, "mode_label": "只读排查"},
                    }
                )
            )
        self.store.update_fields("investigations", investigation_id, {"status": "planned"})
        return tasks

    def _with_counts(self, investigation: dict[str, Any]) -> dict[str, Any]:
        item = dict(investigation)
        item["task_count"] = len(self.list_tasks(item["id"]))
        item["evidence_count"] = len(self.evidence.list_evidence(item["id"]))
        item["root_cause_count"] = len(self.evidence.list_root_causes(item["id"]))
        return item

    def complete_task_with_evidence(self, task_id: str, output_summary: str, raw_excerpt: str = "") -> dict[str, Any] | None:
        task = self.store.get("tasks", task_id)
        if not task:
            return None
        self.store.update_fields(
            "tasks",
            task_id,
            {"status": "completed", "output_summary": output_summary, "finished_at": now_iso()},
        )
        return self.evidence.append_evidence(
            {
                "investigation_id": task["investigation_id"],
                "task_id": task_id,
                "component_id": task.get("target_component_id") or "",
                "source_id": task.get("source_id") or "",
                "evidence_type": "agent_output",
                "title": f"{task.get('agent_role') or 'Agent'} 排查结果",
                "summary": output_summary,
                "raw_excerpt": raw_excerpt,
                "confidence": "discovered",
            }
        )


def get_investigation_service(store: ObservabilityStore | None = None) -> InvestigationService:
    return InvestigationService(store)
