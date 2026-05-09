# OpsCore Agent Context

This file is the repo-root orientation note for future coding agents. Keep it
short, current, and grounded in source files. For hard rules, always prefer
`AGENTS.md`; this file explains the architecture and working map.

## Scope And Boundaries

- Repository root: OpsCore AIOps application workspace.
- External reference code: `.research/hermes-agent/`. Do not edit, format,
  move, delete, or stage anything there unless the user explicitly asks for
  Hermes work.
- Runtime and local state must stay out of product commits: `.env`,
  `.fernet.key`, `opscore.db`, `cron_jobs.sqlite`, `approval_requests.json`,
  `inspection_runs.json`, `protocol_verification_runs.json`,
  `realtime_canvases.json`, `static_react/`, `opscore_lancedb/`, logs,
  screenshots such as `tmp_knowledge_*.png`, and temp directories.
- `knowledge_base/` contains business/user knowledge data. Do not bulk delete or
  auto-ignore it without explicit user confirmation.
- The worktree may contain user edits. Check `git status --short` before edits
  and keep unrelated changes untouched.

## Coding Baseline

This section adapts `bartonzzb/barton-ai-coding-baseline` reviewed at commit
`5f746bf`. Keep `agent.md` as OpsCore's durable baseline/context snapshot; do
not add a separate `BASELINE.md` unless the user asks for it.

- Think before coding. State assumptions when they matter, surface tradeoffs,
  and ask only when local context cannot answer a risky ambiguity.
- Simplicity first. Ship the minimum change that solves the stated problem. Do
  not add speculative features, one-off abstractions, or unused configurability.
- Surgical changes. Touch only the files required for the task, match the local
  style, and mention unrelated cleanup opportunities instead of doing them
  opportunistically.
- Goal-driven execution. Convert work into verifiable success criteria, use
  focused tests or smoke checks that match the blast radius, and loop until the
  evidence supports the conclusion.
- Baseline context discipline. Before significant work, reread `AGENTS.md`,
  this file, and the relevant source entry points. Stay inside the declared
  scope; no deploy, release, destructive cleanup, or out-of-scope subsystem
  changes without explicit user approval.
- Preserve durable context. Update this file when project architecture,
  boundaries, commands, or recurring workflows change. Do not turn it into a
  task log; keep it short, current, and useful to the next agent.

## Stack

- Backend: Python 3.11, FastAPI, Uvicorn, Pydantic v2.
- Agent and model providers: OpenAI SDK, Anthropic SDK, provider/model config
  through `core/llm_factory.py`, `core/model_catalog.py`, and config routes.
- Persistence and integrations: SQLite runtime stores, LanceDB/RAG, Paramiko
  SSH, Python database drivers, WinRM, SNMP, HTTP APIs, object storage,
  virtualization managers, and related protocol adapters.
- Frontend: React 19, TypeScript 5, Vite 7, Tailwind CSS 4, Zustand.
- Vite aliases `@/*` to `frontend/src/*`, proxies `/api` to
  `http://localhost:8000`, and builds into repo-root `static_react/`.

## Common Commands

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
Copy-Item .env.example .env
python main.py
```

Backend default: `http://localhost:8000`. API docs: `/docs`. Health check:
`GET /healthz`.

Before committing OpsCore changes:

```powershell
python scripts/preflight.py --check-git
python scripts/worktree_audit.py --check-staged
```

`scripts/preflight.py --check-git` runs the staged commit gate, backend unit
tests, Python compile, secret scan, `pip check`, frontend `npm audit`, and
frontend build. On Windows, a nested frontend build can hit `spawn EPERM`; if it
does, run `npm run build` directly inside `frontend/` for the strict signal.

CI mirrors the release gate in `.github/workflows/ci.yml`: Python 3.11,
Node 22, backend tests, secret scan, `pip check`, frontend audit, and frontend
build.

## Runtime Entry

- `main.py` loads `.env`, configures logging, creates the FastAPI app, registers
  middleware, includes `api.routes.router` under `/api/v1`, serves legacy
  `/static`, serves React `/assets`, returns `/`, and exposes `/healthz`.
- App startup is delegated to `core/application_lifecycle_service.py`, which
  starts heartbeat, cron scheduling, and background asset hydration.
- `/healthz` is built by `core/health_service.py`. A clean environment can
  return `warning` when the React build is missing; do not assume only
  `status == ok` is acceptable unless the task requires production readiness.
- API token auth applies to `/api/v1/*` except `OPTIONS`.
  `frontend/src/api/http.ts` sends `localStorage.OPSCORE_API_TOKEN` as
  `X-API-Key`.

## Backend Map

- `api/routes.py` is the route aggregator. It imports focused route modules for
  chat, assets, connections, sessions, skills, approvals, dashboards, alerts,
  notifications, config, knowledge, protocol verification, cron/inspection, and
  realtime canvas.
- `api/*_routes.py` should stay thin. Route modules normally validate request
  shape, call `core/*_service.py`, and return `api.schemas.ResponseModel`.
- `api/mappers.py`, `api/schemas.py`, `api/errors.py`, and
  `api/request_models.py` hold response shaping and API error conventions.
- `core/` contains product services, agent runtime, policy, memory, RAG,
  session state, asset catalogs, inspection workflows, dashboard metrics, and
  realtime canvas orchestration.
- `connections/` contains protocol adapters: SSH, database execution, HTTP API,
  SNMP, WinRM, service probes, object/storage platforms, virtualization, Oracle
  client discovery, JDBC, and native SQL helpers.
- `tests/` is broad and mostly unittest based. Prefer targeted tests for the
  files you touched, then `python scripts/preflight.py --check-git` before a
  commit.

## Agent And Tool Flow

Main chat path:

1. `api/chat_routes.py` accepts `/chat` requests.
2. `core/agent.py::chat_stream_agent` prepares a run through
   `core/agent_chat_setup.py`.
3. The run assembles session context, history, memory references, selected
   model, active skills, and protocol-aware tool schemas.
4. `core/agent_chat_loop.py` streams model events and tool calls.
5. `core/dispatcher.py::SkillDispatcher.route_and_execute` enforces safety and
   dispatches the selected tool family.
6. Results are recorded through session/history/memory services and streamed
   back as SSE events.

Important agent components:

- `core/agent.py`: public chat/headless orchestration entrypoints.
- `core/agent_chat_setup.py`, `core/agent_chat_loop.py`: chat preparation and
  streaming loop.
- `core/agent_headless_setup.py`, `core/agent_headless_loop.py`: background
  multi-session/headless task execution.
- `core/agent_protocol_context.py`, `core/agent_session_context.py`: context
  assembly for assets, sessions, and protocols.
- `core/tool_registry.py`: metadata source of truth for available model tools.
  Execution still lives in dispatcher modules.
- `core/dispatcher.py`: safety gate and tool-family router.
- `core/dispatcher_session_tools.py`, `dispatcher_database_tools.py`,
  `dispatcher_api_tools.py`, `dispatcher_memory_tools.py`,
  `dispatcher_scope_tools.py`, `dispatcher_utility_tools.py`,
  `dispatcher_skill_evolution.py`: concrete tool execution families.

Safety path:

- `core/safety_policy.py`, `core/safety_policy_config.py`, and related
  `core/safety_*` modules classify actions, hard-block unsafe requests, enforce
  read-only mode, and determine approval requirements.
- `core/approval_queue.py`, `core/approval_execution_service.py`, and
  `api/approval_routes.py` own pending approvals and execution after decision.
- `local_execute_script` is intentionally restricted by
  `core/local_script_execution.py`; keep execution scoped to active skill paths.

## Skills And Knowledge

- Built-in skills live in `skills/`.
- User/custom skills live in `my_custom_skills/`.
- `core/dispatcher.py` scans both directories for `SKILL.md` and also reads
  external market directories for display-only market skills.
- Skill evolution is a core product capability. Preserve the path through
  `core/dispatcher_skill_evolution.py`, `core/custom_skill_*`, and
  `api/skill_routes.py` when changing skills behavior.
- Knowledge and memory surfaces are currently active and may have user edits:
  `api/knowledge_routes.py`, `core/knowledge_base_service.py`,
  `core/file_memory_store.py`, `core/memory.py`, `core/rag.py`, and frontend
  `KnowledgeBase*` files.

## Frontend Map

- `frontend/src/App.tsx` is the shell. It lazy-loads major views and modals,
  restores active backend sessions on mount, and polls session heartbeats.
- `frontend/src/api/http.ts` is the base request wrapper. Domain API modules
  live beside it, and `frontend/src/api/client.ts` is a compatibility re-export.
- `frontend/src/components/layout/` contains the app chrome: left navigation,
  sidebar, top bar, and toast container.
- `frontend/src/components/views/` contains product views: dashboard, assets,
  realtime canvas, skills, knowledge base, cron, alerts, approvals, and related
  view models/parts.
- `frontend/src/features/sessions/` contains the chat/session workspace:
  sidebar grouping, stream handling, tool traces, approvals, commands,
  attachments, markdown rendering, history sync, and session runtime controls.
- `frontend/src/store/` owns global UI/session state through Zustand.
- Keep visible product UI Chinese-first unless the user asks otherwise. Do not
  translate provider/product brand names just to make them Chinese.

## Common Change Entry Points

- Add or change an API route: update a focused `api/*_routes.py` module, the
  matching `core/*_service.py`, frontend `frontend/src/api/*.ts` client, and
  route tests.
- Change session sidebar metadata or groups: use the narrow backend routes in
  `api/session_runtime_routes.py`; pure group moves should go through
  `/session/{session_id}/group`, not a broad metadata save.
- Change asset support or protocol behavior: inspect `core/asset_*`,
  `core/asset_protocols.py`, `core/tool_registry.py`, and the relevant
  `connections/*_manager.py`.
- Change tool availability: update `core/tool_registry.py` metadata and the
  corresponding dispatcher execution module.
- Change tool safety: update `core/safety_*` and approval tests together.
- Change model/provider settings: use real provider fetch/config results as the
  source of truth; avoid assistant-curated recommendation panels unless the
  user explicitly requests them.
- Change frontend views: follow the existing split between `View.tsx`,
  `ViewParts.tsx`, model/data hooks, and domain API modules. Verify the actual
  served app, especially when port `8000` already has a stale backend process.

## Documentation Sources

- `README.md`: quick start and high-level project map.
- `AGENTS.md`: mandatory repo rules and commit verification requirements.
- `docs/architecture/README.md`: Chinese architecture overview and request flow.
- `docs/deployment-production.md`: production deployment notes.
- `docs/release-checklist.md`: release checklist.
- `docs/runtime_artifact_policy.md`: runtime artifact handling policy.
- `docs/worktree-cleanup.md`: cleanup and archive policy.
