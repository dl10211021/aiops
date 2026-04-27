# OpsCore AIOps

OpsCore is a FastAPI and React based AIOps platform for datacenter operations. It manages assets, runs protocol-aware inspections, routes LLM tool calls through backend safety policies, and exposes dashboards, approval workflows, and production readiness gates.

## Quick Start

```powershell
python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
Copy-Item .env.example .env
python main.py
```

The backend listens on `http://localhost:8000` by default. API docs are available at `http://localhost:8000/docs`, and the health check is `GET /healthz`.

## Quality Gate

Run the full local release gate before committing OpsCore changes:

```powershell
python scripts/preflight.py --check-git
```

This runs the staged worktree audit, backend unit tests, Python compile check, secret scan, dependency check, and frontend build.

## Project Map

- `main.py`: FastAPI app entrypoint, health check, static frontend mount, lifecycle setup.
- `api/`: HTTP routes for chat, assets, inspections, approvals, dashboards, and configuration.
- `core/`: Agent loop, dispatcher, memory, RAG, cron jobs, approval queue, verification logic.
- `connections/`: Protocol managers for SSH, databases, WinRM, SNMP, and related integrations.
- `frontend/`: React/Vite source application.
- `static_react/`: Built frontend assets served by the backend.
- `docs/`: Architecture, deployment, backup, release, and cleanup documentation.
- `tests/`: Unit and contract tests used by local preflight and CI.

## Workspace Boundaries

- `.research/hermes-agent/` contains Hermes source code for reference or explicitly requested Hermes work. Do not edit, format, clean, or stage it during routine OpsCore work.
- Runtime state such as SQLite databases, approval records, inspection runs, logs, `.env`, and `.fernet.key` must stay out of product commits.
- Use `python scripts/worktree_audit.py --check-staged` if you need to inspect what is safe to commit.

## More Documentation

- Architecture guide: `docs/architecture/README.md`
- Production deployment: `docs/deployment-production.md`
- Backup and restore: `docs/backup-restore.md`
- Release checklist: `docs/release-checklist.md`
- Worktree cleanup policy: `docs/worktree-cleanup.md`
