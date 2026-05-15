from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_policy_smoke_covers_execution_policy_and_agent_loop():
    script = (ROOT / "scripts" / "runtime_policy_smoke.py").read_text(encoding="utf-8")

    assert "test_tool_execution_policy.ToolExecutionPolicyTests" in script
    assert "test_runtime_policy_can_require_approval_even_without_safety_hit" in script
    assert "test_runtime_policy_timeout_returns_tool_error" in script
    assert "test_runtime_policy_success_retry_is_attached_to_tool_trace" in script
    assert "test_concurrency_safe_tools_run_in_parallel_batch" in script
    assert "test_mixed_batch_parallelizes_safe_prefix_then_guards_unsafe_tool" in script
    assert '"-m", "unittest"' in script
    assert 'ROOT / "tests"' in script
