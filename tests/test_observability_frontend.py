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
    assert "expandedEvidenceId" in view
    assert "查看详情" in view
    assert "收起详情" in view
    assert "raw_ref: {evidence.raw_ref || '-'}" in view
    assert "evidence.raw_excerpt || '暂无原始摘录'" in view


def test_observability_frontend_surfaces_run_trace_evidence_refs():
    api = Path("frontend/src/api/observability.ts").read_text(encoding="utf-8")
    view = Path("frontend/src/components/views/ObservabilityCenter.tsx").read_text(encoding="utf-8")
    types = Path("frontend/src/types/index.ts").read_text(encoding="utf-8")

    assert "appendObservabilityRunTraceEvidence" in api
    assert "/run-trace-evidence" in api
    assert "session_id: string" in api
    assert "tool_evidence: Record<string, unknown>" in types
    assert "EvidenceReferenceChip" in view
    assert "Run Trace 证据" in view
    assert "runTraceEvidenceId(evidence)" in view
    assert "runTraceEvidenceSessionId(evidence)" in view
    assert "runTraceEvidenceToolName(evidence)" in view
