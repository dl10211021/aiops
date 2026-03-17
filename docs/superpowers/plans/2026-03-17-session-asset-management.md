# OpsCore Session & Asset Management Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign OpsCore's session and asset management to support a three-tier Sub-Agent orchestrator model (Global, Group, Single) and many-to-many tag-based asset grouping, scaling up to 1000+ servers.

**Architecture:** 
- Database: Introduce `tags` and `asset_tags` SQLite tables to replace the single `group_name`.
- Core/Memory: Update `memory_db` to record session `target_scope` and `scope_value` alongside `allow_modifications` (Read-Write toggle).
- Core/Agent & Dispatcher: Implement the Orchestrator pattern for Group sessions. When querying a Group, the master agent will spawn parallel sub-agent tasks using Python's `asyncio.gather` to interrogate individual assets via the SSH/DB managers, summarizing results back to the main context to avoid blowing up the LLM window. All tasks enforce the user-configured Read/Write toggle and have strict `asyncio.wait_for` timeouts.

**Tech Stack:** Python 3.10+, FastAPI, SQLite3, Asyncio, OpenAI AsyncClient (Gemini/OpenAI)

---

### Task 1: Database Schema Migration for Tag-Based Assets

**Files:**
- Modify: `core/memory.py` (specifically `init_db` and related asset saving methods)
- Modify: `connections/db_manager.py` (if any schema checks exist here)
- Create: `patch_tags.py` (a one-off migration script to move existing `group_name` data to the new tables)

- [x] **Step 1: Update SQLite Schema in `init_db`**
Add the creation of `tags` and `asset_tags` tables in `core/memory.py`.

- [x] **Step 2: Update `save_asset` and `get_all_assets`**
Modify `save_asset` to accept a list of tags instead of `group_name`, inserting into the junction table. Modify `get_all_assets` to `GROUP_CONCAT` tags back into the dictionary.

- [x] **Step 3: Create Migration Script (`patch_tags.py`)**
Write a simple Python script that reads `assets` table, creates a tag for the existing `group_name`, inserts into `tags`/`asset_tags`, and drops the `group_name` column.

- [x] **Step 4: Run Migration and Verify**
Run the migration script and ensure the app still starts and `memory_db.get_all_assets()` returns the correct tag lists.

- [x] **Step 5: Commit**
Commit the schema changes and migration script.

---

### Task 2: Session Scoping and Read/Write Flexibility

**Files:**
- Modify: `api/routes.py`
- Modify: `core/memory.py`
- Modify: `core/dispatcher.py`

- [x] **Step 1: Update API to Accept Session Scope**
Modify `/connect` and `/chat` endpoints in `api/routes.py` to handle `target_scope` (global, group, asset) and `scope_value`. Pass `allow_modifications` explicitly based on user choice (Read/Write is flexible).

- [x] **Step 2: Update Session Storage in `ssh_manager.active_sessions`**
Ensure `target_scope` and `allow_modifications` are stored securely in the active session dictionary.

- [x] **Step 3: Update `route_and_execute` Interceptor**
In `core/dispatcher.py`, verify that the regex-based write interception triggers if `allow_modifications` is False. If `allow_modifications` is explicitly set to True by the user for the current session, the interception is bypassed (Read-Write flexibility enabled).

- [x] **Step 4: Test Read/Write Toggle**
Start the server, create a session with `allow_modifications=True`, and attempt a mock write command. It should pass. Then create a session with `allow_modifications=False` and it should block the command.

- [x] **Step 5: Commit**
Commit the API and dispatcher scoping changes.

---

### Task 3: Group Orchestrator & Sub-Agent Dispatch Logic

**Files:**
- Modify: `core/agent.py`
- Modify: `core/dispatcher.py`

- [ ] **Step 1: Create `dispatch_sub_agents` Async Function**
In `core/agent.py`, create a new function `dispatch_group_tasks(tasks: List[Dict], allow_mod: bool)`. This function will use a semaphore (e.g., `asyncio.Semaphore(10)`) to limit concurrency, spinning up headless LLM calls for each target asset to execute its specific check. It MUST wrap each sub-agent execution in an `asyncio.wait_for(task, timeout=60)` block to prevent unresponsive assets from hanging the orchestrator.

- [ ] **Step 2: Expose `execute_on_scope` Tool to Dispatcher**
In `core/dispatcher.py`, when `target_scope == 'group'`, inject a specific JSON schema tool `execute_on_scope(target_assets: List[str], task_instruction: str)`.

- [ ] **Step 3: Hook Tool to Orchestrator**
In `route_and_execute`, map the `execute_on_scope` tool call to the `dispatch_group_tasks` function. It should wait for all sub-agents to finish and return a summarized JSON dictionary of findings.

- [ ] **Step 4: Test Sub-Agent Spawning**
Mock a group with 3 tags. Ask the main agent to "check disk space on the group". Verify logs show 3 separate sub-agent calls being dispatched and aggregated.

- [ ] **Step 5: Commit**
Commit the Sub-Agent Orchestrator logic.

---

### Task 4: Global Scope and Search Tooling

**Files:**
- Modify: `core/dispatcher.py`

- [ ] **Step 1: Inject `search_assets_by_tag` Tool**
When `target_scope == 'global'`, inject a tool that allows the LLM to query the `memory_db` for assets matching specific tags.

- [ ] **Step 2: Restrict Direct Execution in Global**
Ensure `linux_execute_command` is NOT injected when in Global scope, forcing the LLM to use the search tool and rely on the Group/Sub-Agent flow for mass execution.

- [ ] **Step 3: Test Global Search**
Ask the global agent to "find all MES servers". It should use the tool and return the list without attempting SSH.

- [ ] **Step 4: Commit**
Commit the Global scope tooling restrictions.