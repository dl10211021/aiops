from pathlib import Path


def test_observability_frontend_can_append_root_cause_candidates():
    api = Path("frontend/src/api/observability.ts").read_text(encoding="utf-8")
    view = Path("frontend/src/components/views/ObservabilityCenter.tsx").read_text(encoding="utf-8")

    assert "export async function appendObservabilityRootCause" in api
    assert "/root-causes" in api
    assert "supporting_evidence_ids?: string[]" in api
    assert "appendObservabilityRootCause" in view
    assert "appendEvidenceRootCause" in view
    assert "请先追加证据，再生成根因候选" in view
    assert "生成根因候选" in view
    assert "supporting_evidence_ids: evidenceIds.slice(0, 5)" in view
    assert "rootCauseStatusLabel" in view
    assert "已确认" in view
    assert "已驳回" in view
    assert "待复核" in view
    assert "证据 {item.supporting_evidence_ids.length}" in view
    assert "item.recommended_next_steps.slice(0, 3)" in view
