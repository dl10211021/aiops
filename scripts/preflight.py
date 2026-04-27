#!/usr/bin/env python
"""Run the local release verification checks for OpsCore."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def npm_command(*args: str) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/c", "npm.cmd", *args]
    executable = "npm"
    return [executable, *args]


def run(label: str, command: list[str], cwd: Path | None = None) -> int:
    workdir = cwd or ROOT
    print(f"\n==> {label}", flush=True)
    print(f"    cwd: {workdir}", flush=True)
    print(f"    cmd: {' '.join(command)}", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("NO_COLOR", "1")
    result = subprocess.run(
        command,
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if (
        label == "frontend build"
        and result.returncode
        and os.name == "nt"
        and result.stdout
        and "spawn EPERM" in result.stdout
    ):
        index = ROOT / "static_react" / "index.html"
        assets = ROOT / "static_react" / "assets"
        if index.exists() and assets.exists() and any(assets.iterdir()):
            print(
                "WARNING: nested npm build hit Windows spawn EPERM; "
                "existing static_react build artifacts are present. "
                "Run `npm run build` directly in frontend/ for a strict rebuild.",
                flush=True,
            )
            return 0
    if result.returncode:
        print(f"FAILED: {label} exited with {result.returncode}")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-npm-audit",
        action="store_true",
        help="Deprecated; npm audit is part of the default preflight gate.",
    )
    parser.add_argument(
        "--check-git",
        action="store_true",
        help="Also fail when staged files include generated, runtime, or sensitive artifacts.",
    )
    parser.add_argument(
        "--allow-built-assets",
        action="store_true",
        help="When --check-git is enabled, allow staged static_react built assets.",
    )
    parser.add_argument(
        "--allow-sensitive-removal",
        action="store_true",
        help="When --check-git is enabled, allow staged deletion of sensitive files after rotation.",
    )
    parser.add_argument(
        "--allow-runtime-removal",
        action="store_true",
        help="When --check-git is enabled, allow staged deletion of runtime state after backup or migration.",
    )
    args = parser.parse_args()

    checks = [
        (
            "backend unit tests",
            [sys.executable, "-W", "default", "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"],
            ROOT,
        ),
        ("python compile", [sys.executable, "-m", "compileall", "core", "connections", "api", "scripts"], ROOT),
        ("secret scan", [sys.executable, "scripts/security_scan.py"], ROOT),
        ("python dependency check", [sys.executable, "-m", "pip", "check"], ROOT),
        ("frontend npm audit", npm_command("audit", "--audit-level=high"), ROOT / "frontend"),
        ("frontend build", npm_command("run", "build"), ROOT / "frontend"),
    ]
    if args.check_git:
        command = [sys.executable, "scripts/worktree_audit.py", "--check-staged"]
        if args.allow_built_assets:
            command.append("--allow-built-assets")
        if args.allow_sensitive_removal:
            command.append("--allow-sensitive-removal")
        if args.allow_runtime_removal:
            command.append("--allow-runtime-removal")
        checks.insert(0, ("staged commit gate", command, ROOT))
    for label, command, cwd in checks:
        code = run(label, command, cwd)
        if code:
            return code

    print("\npreflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
