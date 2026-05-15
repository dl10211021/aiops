from pathlib import Path


def test_tool_policy_runtime_summary_exposes_operational_context():
    source = Path(
        "frontend/src/features/sessions/ToolPolicyRuntimeSummary.tsx"
    ).read_text(encoding="utf-8")

    assert "强审批" in source
    assert "受控执行" in source
    assert "只读安全" in source
    assert "调度边界" in source
    assert "超时与重试" in source
    assert "不会被自动并发放大风险" in source
