# OpsCore Worktree Cleanup Guide

## Purpose

The current repository has accumulated generated files, runtime state, local logs, and historical tracked dependencies. Cleanup must be conservative because the same workspace also contains real assets, encrypted credentials, model provider config, approval audit records, and inspection evidence.

## Audit Command

```powershell
python scripts/worktree_audit.py
python scripts/worktree_audit.py --json
python scripts/worktree_audit.py --check-staged
python scripts/preflight.py --check-git
```

The audit is read-only. It does not delete files, reset git, or rewrite history.

`--check-staged` is a commit gate. It returns a non-zero exit code when staged files would add or modify dependency artifacts, secrets, runtime state, logs, temporary files, or frontend build output that was not explicitly allowed.

Cleanup deletions for `node_modules`, logs, temporary files, and old generated assets are allowed because they remove noise from the repository. Secret and runtime-state deletions are still blocked by default because they need an explicit rotation, backup, or migration decision.

Use `--allow-built-assets` only when `static_react` assets are intentionally served from this repository:

```powershell
python scripts/worktree_audit.py --check-staged --allow-built-assets
python scripts/preflight.py --check-git --allow-built-assets
```

TypeScript build cache such as `frontend/tsconfig.tsbuildinfo` remains blocked even when built assets are allowed.

Use the sensitive/runtime removal flags only after backup, migration, and secret rotation have been handled:

```powershell
python scripts/worktree_audit.py --check-staged --allow-sensitive-removal --allow-runtime-removal
python scripts/preflight.py --check-git --allow-sensitive-removal --allow-runtime-removal
```

## Git State Fields

The report separates file category from Git state:

- `stage=staged`: the Git index already contains a change, for example `D  .fernet.key`.
- `stage=unstaged`: the working tree changed but the index has not, for example ` D static_react/assets/index-old.js`.
- `stage=staged_and_unstaged`: the same path has both index and working tree changes.
- `stage=untracked`: the path is new to Git, for example `?? static_react/assets/index-new.js`.

Use `stage_summary` to understand whether the noise is already staged or only local. A staged deletion is not the same as a local file being deleted during cleanup; it means the index currently records that deletion.

## Categories

- `product_change`: source code, tests, docs, frontend source, or configuration intended for review.
- `dependency_artifact`: `frontend/node_modules` or similar vendored dependency output. Do not restore this into git.
- `sensitive_runtime_state`: `.env`, `.fernet.key`, `providers.json`, `safety_policy.json`, `models.json`. Do not commit these or their deletion without an explicit secret-rotation plan.
- `runtime_state`: SQLite, approval records, inspection runs, templates, memory and knowledge stores. Back up before cleanup.
- `runtime_output`: logs and command output files. Usually safe to ignore or delete after confirming no incident evidence is needed.
- `frontend_build_artifact`: `static_react` generated assets and TypeScript build cache. Commit only if this repository intentionally serves built frontend assets.
- `temporary_artifact`: patch/fix/update scripts, tmp files, local debug helpers.

## Safe Cleanup Policy

1. Back up `runtime_state` and `sensitive_runtime_state`.
2. Never use `git reset --hard` for cleanup in this workspace.
3. Never recursively delete broad paths without verifying the absolute target path.
4. Remove tracked generated files from the Git index only after review, for example `git rm --cached -r frontend/node_modules`.
5. Commit product changes in logical groups: backend, frontend, tests, docs, generated static frontend if required.
6. Treat staged secret deletion as a deliberate secret-rotation change, not as incidental cleanup.
7. Keep `runtime_state_do_not_commit` paths local or mounted in production storage.
8. Run `python scripts/preflight.py --check-git` before a release commit.

## Current High-Risk Items To Review

- `.fernet.key` appears in git status as deleted. Treat this as secret material; rotate and remove from Git history/index deliberately, not as an incidental cleanup.
- `frontend/node_modules` appears as tracked deletion noise. The correct long-term state is generated locally by `npm ci`, not stored in Git.
- Runtime databases and JSON audit files must be mounted or backed up in production, not committed.
- `static_react/assets` contains old generated asset deletions and new generated asset files after frontend builds. Commit them only if static assets are intentionally served from the repository.

## Commit Grouping

`python scripts/worktree_audit.py --json` includes these helper groups:

- `source_product_changes`: source, tests, docs, and configuration to review as normal product changes.
- `generated_frontend_assets`: built frontend assets to either commit or move to deployment-time build output.
- `index_cleanup_required`: staged generated/sensitive/runtime-output entries that require deliberate Git index cleanup.
- `runtime_state_do_not_commit`: local state and secrets that should not be part of product commits.

## Rollback

If cleanup removes something needed locally, restore from backup first. Use Git only for tracked source files and avoid using Git to restore secrets or runtime state unless you have verified the repository is allowed to contain them.
