# Safety Policy Action UI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the safety policy modal so baseline operators can configure approval and deny rules without understanding regex, while preserving advanced raw-rule editing.

**Architecture:** Keep the existing backend policy contract for this first phase. Add a semantic UI layer in `SafetyPolicyModal.tsx` that maps user-friendly action groups to existing policy fields such as `approval_patterns`, `readonly_block_patterns`, `approval_methods`, and `hard_block_substrings`.

**Tech Stack:** React 19, TypeScript, Tailwind CSS 4, existing Zustand modal/toast store, existing `/config/safety-policy` API.

---

### Task 1: Replace Regex-First Modal With Action-First UI

**Files:**
- Modify: `frontend/src/components/modals/SafetyPolicyModal.tsx`

- [ ] Add resource-domain definitions for OS, database, Kubernetes/API, virtualization, network, storage/S3, monitoring, hardware, and platform capabilities.
- [ ] Add an action summary table with clear labels for allowed, approval, and denied behavior.
- [ ] Keep existing category editing under an advanced details section.
- [ ] Ensure readonly mode is explained as a system behavior, not exposed as a separate user-facing rule family.

### Task 2: Add Simple Rule Form

**Files:**
- Modify: `frontend/src/components/modals/SafetyPolicyModal.tsx`

- [ ] Add a form for rule name, resource domain, platform, matcher type, matcher value, and handling mode.
- [ ] Map approval rules into the current backend fields.
- [ ] Map deny rules into `hard_block_substrings`.
- [ ] For command-like categories, mirror approval patterns into readonly block patterns so readonly sessions continue blocking change actions.
- [ ] Show a concise explanation of how the new rule will behave in readonly and readwrite sessions.

### Task 3: Verify Frontend Build

**Files:**
- Modify generated assets under `static_react/` after build.

- [ ] Run `npm run build` in `frontend`.
- [ ] Run the project preflight with built assets allowed.
- [ ] Commit and push if verification passes.
