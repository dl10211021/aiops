#!/usr/bin/env python
"""Run the focused runtime-policy smoke checks."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SMOKE_TESTS = [
    "test_tool_execution_policy.ToolExecutionPolicyTests",
    "test_agent_tool_loop.AgentToolLoopTests.test_runtime_policy_can_require_approval_even_without_safety_hit",
    "test_agent_tool_loop.AgentToolLoopTests.test_runtime_policy_timeout_returns_tool_error",
    "test_agent_tool_loop.AgentToolLoopTests.test_runtime_policy_success_retry_is_attached_to_tool_trace",
    "test_agent_tool_loop.AgentToolLoopTests.test_concurrency_safe_tools_run_in_parallel_batch",
    "test_agent_tool_loop.AgentToolLoopTests.test_mixed_batch_parallelizes_safe_prefix_then_guards_unsafe_tool",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the unittest targets without running them.",
    )
    args = parser.parse_args(argv)

    if args.list:
        for target in SMOKE_TESTS:
            print(target)
        return 0

    command = [sys.executable, "-m", "unittest", *SMOKE_TESTS]
    env = os.environ.copy()
    python_path = [str(ROOT), str(ROOT / "tests")]
    existing_python_path = env.get("PYTHONPATH")
    if existing_python_path:
        python_path.append(existing_python_path)
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    print("runtime policy smoke checks:")
    for target in SMOKE_TESTS:
        print(f"- {target}")
    return subprocess.run(command, cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
