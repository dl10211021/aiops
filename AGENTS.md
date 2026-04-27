# OpsCore Agent Rules

## Project Scope

- Treat this repository root as the OpsCore AIOps application workspace.
- `.research/hermes-agent/` contains Hermes source code for reference or separate work. It is not part of routine OpsCore cleanup, formatting, refactoring, or release commits.
- Do not edit, delete, move, format, or stage files under `.research/hermes-agent/` unless the user explicitly asks for Hermes work.
- If Hermes changes appear in `git status`, stop and ask before including them in an OpsCore commit.

## Verification

- Run `python scripts/preflight.py --check-git` before committing OpsCore changes.
- Use `python scripts/worktree_audit.py --check-staged` to catch generated, runtime, sensitive, or external-source files before commit.
