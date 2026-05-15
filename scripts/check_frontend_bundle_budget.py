#!/usr/bin/env python
"""Validate production frontend bundle size and eager preload boundaries."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENTRY_BUDGET_BYTES = 150_000


def _entry_scripts(index_html: str) -> list[str]:
    return re.findall(r'<script[^>]+src="/assets/([^"]+)"', index_html)


def _module_preloads(index_html: str) -> list[str]:
    return re.findall(r'<link[^>]+rel="modulepreload"[^>]+href="/assets/([^"]+)"', index_html)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entry-budget-bytes",
        type=int,
        default=DEFAULT_ENTRY_BUDGET_BYTES,
        help=f"Maximum allowed eager entry JS size. Default: {DEFAULT_ENTRY_BUDGET_BYTES}",
    )
    args = parser.parse_args()

    build_dir = ROOT / "static_react"
    index_path = build_dir / "index.html"
    assets_dir = build_dir / "assets"
    if not index_path.exists() or not assets_dir.exists():
        print("frontend bundle budget failed: static_react build artifacts are missing")
        return 1

    index_html = index_path.read_text(encoding="utf-8")
    entry_scripts = _entry_scripts(index_html)
    if not entry_scripts:
        print("frontend bundle budget failed: no entry script found in static_react/index.html")
        return 1

    failures: list[str] = []
    for script in entry_scripts:
        script_path = assets_dir / script
        if not script_path.exists():
            failures.append(f"entry script missing: {script}")
            continue
        size = script_path.stat().st_size
        if size > args.entry_budget_bytes:
            failures.append(
                f"entry script {script} is {size} bytes; budget is {args.entry_budget_bytes}"
            )

    preloads = _module_preloads(index_html)
    terminal_preloads = [item for item in preloads if "vendor-terminal" in item]
    if terminal_preloads:
        failures.append(
            "terminal vendor chunk must stay lazy-loaded, but index.html preloads: "
            + ", ".join(terminal_preloads)
        )

    if failures:
        print("frontend bundle budget failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    entry_summary = ", ".join(
        f"{script}={((assets_dir / script).stat().st_size / 1024):.1f} KiB"
        for script in entry_scripts
        if (assets_dir / script).exists()
    )
    preload_summary = ", ".join(preloads) or "none"
    print(
        "frontend bundle budget passed: "
        f"entries [{entry_summary}], modulepreload [{preload_summary}]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
