#!/usr/bin/env python
"""Classify git worktree changes without deleting or reverting anything."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SENSITIVE_FILES = {
    ".env",
    ".fernet.key",
    "providers.json",
    "safety_policy.json",
    "models.json",
}

RUNTIME_STATE_SUFFIXES = {
    ".db",
    ".sqlite",
}

RUNTIME_STATE_NAMES = {
    "approval_requests.json",
    "inspection_runs.json",
    "inspection_templates.json",
    "protocol_verification_runs.json",
    "verification_runs.json",
}


def _split_status(status: str) -> tuple[str, str]:
    if status == "??":
        return "?", "?"
    if len(status) >= 2:
        return status[0], status[1]
    if len(status) == 1:
        return status[0], " "
    return " ", " "


def _stage(index_status: str, worktree_status: str) -> str:
    if index_status == "?" and worktree_status == "?":
        return "untracked"
    index_changed = index_status not in {" ", "?"}
    worktree_changed = worktree_status not in {" ", "?"}
    if index_changed and worktree_changed:
        return "staged_and_unstaged"
    if index_changed:
        return "staged"
    if worktree_changed:
        return "unstaged"
    return "clean"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def parse_porcelain_line(line: str) -> dict[str, str]:
    if not line:
        raise ValueError("empty porcelain status line")
    if len(line) < 3:
        raise ValueError(f"invalid porcelain status line: {line!r}")

    index_status, worktree_status = _split_status(line[:2])
    return {
        "path": _normalize(line[3:]),
        "status": line[:2],
        "index_status": index_status,
        "worktree_status": worktree_status,
        "stage": _stage(index_status, worktree_status),
    }


def _with_git_state(item: dict[str, object], status: str) -> dict[str, object]:
    index_status, worktree_status = _split_status(status)
    item["status"] = status
    item["index_status"] = index_status
    item["worktree_status"] = worktree_status
    item["stage"] = _stage(index_status, worktree_status)
    return item


def classify_path(status: str, path: str) -> dict[str, object]:
    normalized = _normalize(path)
    name = Path(normalized).name
    suffix = Path(normalized).suffix.lower()
    deleted = "D" in status

    if normalized.startswith("frontend/node_modules/") or "/node_modules/" in normalized:
        return _with_git_state({
            "path": normalized,
            "category": "dependency_artifact",
            "requires_human_review": True,
            "recommendation": "Do not restore vendor files. After confirming package-lock is correct, remove tracked node_modules with git rm --cached.",
        }, status)

    if name in SENSITIVE_FILES:
        action = "Rotate or restore from secure backup" if deleted else "Keep local only"
        return _with_git_state({
            "path": normalized,
            "category": "sensitive_runtime_state",
            "requires_human_review": True,
            "recommendation": f"{action}; do not commit this file or its deletion without an explicit secret-rotation plan.",
        }, status)

    if suffix in RUNTIME_STATE_SUFFIXES or name in RUNTIME_STATE_NAMES or normalized.startswith(("memory/", "opscore_lancedb/", "data/")):
        return _with_git_state({
            "path": normalized,
            "category": "runtime_state",
            "requires_human_review": True,
            "recommendation": "Back up before cleanup. Usually keep out of git and migrate to mounted production storage.",
        }, status)

    if suffix == ".log" or normalized.endswith((".out.log", ".err.log")) or "/logs/" in normalized:
        return _with_git_state({
            "path": normalized,
            "category": "runtime_output",
            "requires_human_review": False,
            "recommendation": "Safe to ignore or delete after confirming no incident evidence is needed.",
        }, status)

    if normalized.startswith("static_react/assets/") or normalized == "static_react/index.html" or suffix == ".tsbuildinfo":
        return _with_git_state({
            "path": normalized,
            "category": "frontend_build_artifact",
            "requires_human_review": False,
            "recommendation": "Commit only if this repository intentionally stores built frontend assets; otherwise ignore and build during deployment.",
        }, status)

    if (
        normalized.startswith(".agents/")
        or normalized.startswith("tmp")
        or name.startswith(("patch_", "fix_", "update_"))
        or normalized in {
            "tmp_history.json",
            ".git_log_frontend.txt",
            "test_chat.py",
            "test_chat_backend.py",
            "test_superpowers.py",
            "test_vllm.py",
        }
    ):
        return _with_git_state({
            "path": normalized,
            "category": "temporary_artifact",
            "requires_human_review": False,
            "recommendation": "Safe to ignore or delete after confirming it is not needed for debugging.",
        }, status)

    return _with_git_state({
        "path": normalized,
        "category": "product_change",
        "requires_human_review": True,
        "recommendation": "Review diff and include in a focused commit if it is part of the intended product change.",
    }, status)


def _is_staged(item: dict[str, object]) -> bool:
    return str(item.get("stage")) in {"staged", "staged_and_unstaged"}


def _is_frontend_cache(path: str) -> bool:
    return Path(path).suffix.lower() == ".tsbuildinfo"


def _is_staged_deletion(item: dict[str, object]) -> bool:
    return str(item.get("index_status")) == "D"


def commit_blockers(
    items: list[dict[str, object]],
    *,
    allow_built_assets: bool = False,
    allow_sensitive_removal: bool = False,
    allow_runtime_removal: bool = False,
) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    blocked_when_added_or_modified = {
        "dependency_artifact",
        "runtime_output",
        "temporary_artifact",
    }
    always_blocked_categories = {
        "sensitive_runtime_state",
        "runtime_state",
    }
    for item in items:
        if not _is_staged(item):
            continue
        category = str(item.get("category"))
        path = str(item.get("path"))
        reason = ""
        if category == "sensitive_runtime_state" and _is_staged_deletion(item) and allow_sensitive_removal:
            continue
        if category == "runtime_state" and _is_staged_deletion(item) and allow_runtime_removal:
            continue
        if category in always_blocked_categories:
            reason = f"{category} must not be committed from this workspace."
        elif category in blocked_when_added_or_modified and not _is_staged_deletion(item):
            reason = f"{category} content must not be committed from this workspace."
        elif category == "frontend_build_artifact":
            if _is_frontend_cache(path) and not _is_staged_deletion(item):
                reason = "TypeScript build cache must not be committed."
            elif not allow_built_assets and not _is_staged_deletion(item):
                reason = "Built frontend assets require --allow-built-assets."
        if reason:
            blocked = dict(item)
            blocked["block_reason"] = reason
            blockers.append(blocked)
    return blockers


def git_status_porcelain() -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or "git status failed")
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        entries.append(parse_porcelain_line(line))
    return entries


def build_report() -> dict[str, object]:
    items = [classify_path(entry["status"], entry["path"]) for entry in git_status_porcelain()]
    summary: dict[str, int] = {}
    stage_summary: dict[str, int] = {}
    for item in items:
        category = str(item["category"])
        summary[category] = summary.get(category, 0) + 1
        stage = str(item["stage"])
        stage_summary[stage] = stage_summary.get(stage, 0) + 1
    return {
        "summary": summary,
        "stage_summary": stage_summary,
        "commit_groups": {
            "source_product_changes": [item["path"] for item in items if item["category"] == "product_change"],
            "generated_frontend_assets": [item["path"] for item in items if item["category"] == "frontend_build_artifact"],
            "index_cleanup_required": [
                item["path"]
                for item in items
                if item["stage"] in {"staged", "staged_and_unstaged"}
                and item["category"] in {"dependency_artifact", "sensitive_runtime_state", "runtime_output"}
            ],
            "runtime_state_do_not_commit": [
                item["path"]
                for item in items
                if item["category"] in {"runtime_state", "sensitive_runtime_state"}
            ],
        },
        "items": items,
        "commit_blockers": commit_blockers(items),
        "next_steps": [
            "Back up runtime_state and sensitive_runtime_state before any cleanup.",
            "Remove tracked dependency_artifact entries from git index only after human confirmation.",
            "Commit product_change entries in focused groups after review.",
            "Do not use git reset --hard or recursive deletes for this cleanup.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    parser.add_argument("--check-staged", action="store_true", help="Fail if staged files include generated, runtime, or sensitive artifacts.")
    parser.add_argument("--allow-built-assets", action="store_true", help="Allow staged static_react built assets, but never TypeScript build cache.")
    parser.add_argument("--allow-sensitive-removal", action="store_true", help="Allow staged deletion of sensitive files after an explicit rotation decision.")
    parser.add_argument("--allow-runtime-removal", action="store_true", help="Allow staged deletion of runtime state after backup or migration.")
    args = parser.parse_args()

    report = build_report()
    blockers = commit_blockers(
        report["items"],
        allow_built_assets=args.allow_built_assets,
        allow_sensitive_removal=args.allow_sensitive_removal,
        allow_runtime_removal=args.allow_runtime_removal,
    )
    report["commit_blockers"] = blockers
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if args.check_staged and blockers else 0

    print("Worktree hygiene report")
    for category, count in sorted(report["summary"].items()):
        print(f"- {category}: {count}")
    print("\nStage summary:")
    for stage, count in sorted(report["stage_summary"].items()):
        print(f"- {stage}: {count}")
    if args.check_staged:
        print("\nStaged commit gate:")
        if blockers:
            print(f"- failed: {len(blockers)} blocker(s)")
            for item in blockers[:20]:
                print(f"- {item['path']}: {item['block_reason']}")
            if len(blockers) > 20:
                print(f"- ... {len(blockers) - 20} more blocker(s)")
        else:
            print("- passed: no staged generated, runtime, or sensitive artifacts")
    print("\nNext steps:")
    for step in report["next_steps"]:
        print(f"- {step}")
    return 1 if args.check_staged and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
