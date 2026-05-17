# OpsCore Agent Rules

## Project Scope

- Treat this repository root as the OpsCore AIOps application workspace.
- `.research/hermes-agent/` contains Hermes source code for reference or separate work. It is not part of routine OpsCore cleanup, formatting, refactoring, or release commits.
- Do not edit, delete, move, format, or stage files under `.research/hermes-agent/` unless the user explicitly asks for Hermes work.
- If Hermes changes appear in `git status`, stop and ask before including them in an OpsCore commit.

## Verification

- Run `python scripts/preflight.py --check-git` before committing OpsCore changes.
- Use `python scripts/worktree_audit.py --check-staged` to catch generated, runtime, sensitive, or external-source files before commit.

## Architecture Boundary

- Keep OpsCore architecture decoupled. Do not solve new product needs by wiring observability, alerts, inspection, knowledge, memory, approval, notification, multi-agent dispatch, and asset/session runtime directly into each other.
- Route cross-cutting work through explicit service contracts and event/run records first, then attach UI or feature-specific behavior on top. Prefer contracts such as `AIOps Run`, `Run Trace`, `Tool Policy`, `Approval Request`, `Evidence Ref`, and `Learning Candidate` over ad hoc module-to-module calls.
- Follow the useful Hermes architecture pattern in spirit: tool registration and toolsets are composable, context handling is pluggable, memory read/write paths are separated, gateway/channel concerns are isolated, and profile/runtime state has clear ownership. Adapt those ideas to OpsCore's AIOps domain instead of copying Hermes code.
- If a change would require a feature module to import another unrelated feature module, stop and introduce or reuse a neutral core service, DTO, or event contract instead.
- Frontend UX should stay simple even when backend governance is rich. Hide internal state machines, quality gates, and audit internals behind concise actions and progressive detail views.
- Preserve lifecycle hook and runtime loop boundaries. New observability, inspection, notification, approval, memory, learning, or multi-agent behavior should attach through explicit events such as `run:start`, `agent:step`, `tool:before`, `tool:after`, `approval:requested`, `approval:resolved`, `memory:candidate`, `context:compact`, `notification:sent`, and `run:end` rather than direct feature imports.
- Runtime loops must have visible budgets and stop conditions: max turns, timeout, cancellation, heartbeat, duplicate-action/spin detection, retry limits, and structured finalization. Never add a background loop or scheduled loop without these controls.
- Treat tool coverage as a toolset inventory problem. Compare against Hermes toolsets when adding tools, but expose only OpsCore-relevant tools through policy metadata, approval gates, evidence capture, and simple UI grouping.
- Prompt changes are architecture changes. Keep prompts modular, versioned, evidence-first, and permission-aware. AIOps prompts must prefer live tool evidence over memory, avoid leaking credentials or hidden context, and route learning through auxiliary review plus human confirmation before durable Skill/Runbook promotion.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **skillops-main** (22768 symbols, 38694 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/skillops-main/context` | Codebase overview, check index freshness |
| `gitnexus://repo/skillops-main/clusters` | All functional areas |
| `gitnexus://repo/skillops-main/processes` | All execution flows |
| `gitnexus://repo/skillops-main/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
