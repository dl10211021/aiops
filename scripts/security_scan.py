#!/usr/bin/env python
"""Fail fast on obvious secrets in source-controlled project files."""

from __future__ import annotations

import argparse
import subprocess
import re
import sys
from pathlib import Path


DEFAULT_EXCLUDES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".research",
    "__pycache__",
    "build",
    "data",
    "dist",
    "frontend/node_modules",
    "memory",
    "node_modules",
    "opscore_lancedb",
    "static_react/assets",
    "temp_sandbox",
}

DEFAULT_PATHS = [
    ".gitignore",
    "api",
    "connections",
    "core",
    "frontend/src",
    "main.py",
    "requirements.txt",
    "scripts",
    "tests",
]

SECRET_PATTERNS = [
    ("gpustack_api_key", re.compile(r"gpustack_[A-Za-z0-9_]{24,}", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("password_assignment", re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*['\"]([^'\"\n]{8,})['\"]")),
    ("api_key_assignment", re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|bearer[_-]?token)\b\s*[:=]\s*['\"][^'\"\n]{16,}['\"]")),
]

TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def tracked_and_unignored_files(root: Path, paths: list[str]) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *paths],
            cwd=root,
            capture_output=True,
            check=True,
            text=True,
        )
    except Exception:
        return None
    return [root / line for line in result.stdout.splitlines() if line.strip()]


def is_excluded(path: Path, root: Path, excludes: set[str]) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    for item in excludes:
        if rel == item or rel.startswith(f"{item}/") or item in parts:
            return True
    return False


def is_text_candidate(path: Path) -> bool:
    if path.name in {".env", ".env.local", ".gitignore"}:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def iter_files(root: Path, paths_to_scan: list[str], excludes: set[str]):
    paths = tracked_and_unignored_files(root, paths_to_scan)
    if paths is None:
        paths = []
        for item in paths_to_scan:
            candidate = root / item
            if candidate.is_file():
                paths.append(candidate)
            elif candidate.is_dir():
                paths.extend(candidate.rglob("*"))
    for path in paths:
        if not path.is_file():
            continue
        if is_excluded(path, root, excludes):
            continue
        if is_text_candidate(path):
            yield path


def scan_file(path: Path, root: Path):
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        yield (path.relative_to(root).as_posix(), "read_error", str(exc))
        return

    for name, pattern in SECRET_PATTERNS:
        for line_no, line in enumerate(lines, start=1):
            rel = path.relative_to(root).as_posix()
            if name == "password_assignment" and rel.startswith("tests/"):
                continue
            if "allow-secret" in line or is_placeholder_line(line):
                continue
            if pattern.search(line):
                yield (rel, name, f"line {line_no}")


def is_placeholder_line(line: str) -> bool:
    lowered = line.lower()
    placeholders = {
        "example",
        "fake",
        "dummy",
        "placeholder",
        "changeme",
        "replace with",
        "your-",
        "your_",
        '"password"',
        "'password'",
        "password123",
        "ops_core_auto_injected",
        "opscore_auto_injected",
    }
    if any(item in lowered for item in placeholders):
        return True
    compact = re.sub(r"[^a-z0-9]", "", lowered)
    if compact and len(set(compact)) <= 3:
        return True
    if "111111" in compact or "222222" in compact:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root to scan.")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional relative path or directory to skip. Can be repeated.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Relative file or directory to scan. Defaults to main application code paths.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    excludes = DEFAULT_EXCLUDES | {item.replace("\\", "/").strip("/") for item in args.exclude}
    paths_to_scan = [item.replace("\\", "/").strip("/") for item in args.path] or DEFAULT_PATHS
    findings = []
    for path in iter_files(root, paths_to_scan, excludes):
        findings.extend(scan_file(path, root))

    if findings:
        for rel, name, detail in findings:
            print(f"{rel}: {name}: {detail}")
        return 1

    print("security scan passed: no obvious secrets found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
