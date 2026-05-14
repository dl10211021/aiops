#!/usr/bin/env python
"""Validate OpsCore runtime tool policy metadata."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.tool_policy_validation import validate_tool_runtime_policies  # noqa: E402
from core.tool_registry import tool_registry  # noqa: E402


def main() -> int:
    issues = validate_tool_runtime_policies(tool_registry.all_tools())
    if issues:
        print("tool policy validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"tool policy validation passed: {len(tool_registry.all_tools())} tools")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
