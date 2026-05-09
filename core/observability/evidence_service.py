from __future__ import annotations

from typing import Any

from core.observability.models import Evidence, RootCauseCandidate
from core.observability.store import ObservabilityStore, get_observability_store


class EvidenceService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def append_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = Evidence(**payload)
        return self.store.upsert("evidence", evidence.to_record())

    def list_evidence(self, investigation_id: str) -> list[dict[str, Any]]:
        return self.store.list("evidence", where="investigation_id = ?", params=(investigation_id,), order_by="created_at ASC")

    def append_root_cause_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate = RootCauseCandidate(**payload)
        return self.store.upsert("root_causes", candidate.to_record())

    def list_root_causes(self, investigation_id: str) -> list[dict[str, Any]]:
        return self.store.list("root_causes", where="investigation_id = ?", params=(investigation_id,), order_by="likelihood DESC, created_at ASC")

    def attach_alert_event(self, investigation_id: str, alert: dict[str, Any]) -> dict[str, Any]:
        return self.append_evidence(
            {
                "investigation_id": investigation_id,
                "evidence_type": "alert",
                "title": str(alert.get("alert_name") or alert.get("id") or "告警事件"),
                "summary": str(alert.get("description") or alert.get("summary") or ""),
                "raw_ref": str(alert.get("id") or ""),
                "raw_excerpt": str(alert)[:1200],
                "confidence": "confirmed",
                "metadata": {"source": "alerts", "alert": alert},
            }
        )

    def attach_inspection_result(self, investigation_id: str, inspection: dict[str, Any]) -> dict[str, Any]:
        return self.append_evidence(
            {
                "investigation_id": investigation_id,
                "evidence_type": "inspection",
                "title": str(inspection.get("title") or inspection.get("run_id") or "巡检结果"),
                "summary": str(inspection.get("summary") or inspection.get("status") or ""),
                "raw_ref": str(inspection.get("run_id") or inspection.get("id") or ""),
                "raw_excerpt": str(inspection)[:1200],
                "confidence": "confirmed",
                "metadata": {"source": "inspection", "inspection": inspection},
            }
        )

    def attach_canvas_reference(self, investigation_id: str, canvas_item: dict[str, Any]) -> dict[str, Any]:
        return self.append_evidence(
            {
                "investigation_id": investigation_id,
                "evidence_type": "canvas",
                "title": str(canvas_item.get("title") or "画板视图"),
                "summary": "已关联实时画板视图，可用于排查上下文。",
                "raw_ref": str(canvas_item.get("id") or ""),
                "raw_excerpt": "",
                "confidence": "confirmed",
                "metadata": {"source": "canvas", "canvas": canvas_item},
            }
        )


def get_evidence_service(store: ObservabilityStore | None = None) -> EvidenceService:
    return EvidenceService(store)
