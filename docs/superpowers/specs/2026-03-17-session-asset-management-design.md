# OpsCore Session & Asset Management Redesign Spec

## 1. Overview
This specification details the redesign of the session and asset management system in OpsCore. The new design shifts from a flat server list to a hierarchical, orchestrator-driven Sub-Agent model tailored for AIOps RCA (Root Cause Analysis) and health checks across single assets, business groups, and global environments.

All three session scopes support flexible Read/Write permissions configured by the user via the `allow_modifications` toggle.

## 2. The Three-Tier Session Architecture

### 2.1 Single Asset Session
- **Definition**: A 1:1 interaction with a specific server or database (e.g., a single Linux host).
- **Tooling**: Directly loads targeted Skills (e.g., `Linux-Check.md`, `MySQL-Tuning.md`) relevant to the OS/Protocol.
- **Execution**: Runs commands directly via `connections/ssh_manager.py` (or db_manager).
- **Safety**: Validates the `allow_modifications` flag before executing any write/destructive commands (e.g., `rm`, `drop`). If false, blocks at the regex/dispatcher level.

### 2.2 Business Group Session (Orchestrator Mode)
- **Definition**: A logical business group (e.g., "MES System") that contains multiple heterogeneous assets (Linux servers, MySQL databases, Network switches).
- **Tooling & Prompts**: Loads the Business Group context and a "System Architect/Orchestrator" prompt. It does *not* execute commands directly.
- **Sub-Agent Dispatching**: 
  - The Group Agent acts as an orchestrator. When asked to "inspect the MES system", it analyzes the system architecture.
  - It spawns isolated **Sub-Agents** for each component (e.g., one sub-agent for the MES database, one for the MES network).
  - Each Sub-Agent is effectively a "Single Asset Session" that runs its own checks and reports back.
- **Result Aggregation**: The Group Agent waits for all sub-agents to complete, synthesizes the findings (e.g., "The network is fine, but the MES DB has slow queries"), and responds to the user.
- **Safety**: The `allow_modifications` constraint is passed down recursively to every spawned Sub-Agent.

### 2.3 Global Session
- **Definition**: The top-level command center with visibility across all 1000+ assets in the enterprise.
- **Tooling**: Primarily equipped with search and metadata tools (`search_assets_by_tag`, `list_business_groups`). 
- **Execution**: Can execute commands globally, but relies on the same Sub-Agent dispatch mechanism as the Group Session to prevent context overflow.
- **Safety**: Inherits the `allow_modifications` permission to control global destructive commands.

## 3. Data Model Changes (Asset Tags)
To support querying and grouping 1000+ assets into Business Groups:
- **Current State**: Assets have a single `group_name` column.
- **New State**: Assets will support multiple tags/groups. 
  - To support 1000+ assets efficiently, we will introduce a normalized many-to-many relationship: `assets`, `tags`, and `asset_tags` tables. 
  - A tag like `sys:MES` will group all related assets into the MES Business Group.

## 4. Sub-Agent Dispatch Flow
When a Group Agent needs to inspect the "MES System":
1. **Resolution**: Group Agent queries the DB for all assets tagged `sys:MES`.
2. **Task Generation**: Group Agent generates inspection prompts for each asset type (e.g., "Check slow queries" for DB).
3. **Dispatch**: Group Agent calls `dispatch_sub_agents(tasks=[...])`.
4. **Execution**: Backend asynchronously spins up isolated LLM contexts (Sub-Agents) for each task.
5. **Collection**: Backend collects Sub-Agent summaries and returns them to the Group Agent's context.

## 5. Error Handling & Limitations
- **Context Window Limits**: Sub-Agents must return concise summaries, not raw logs, to the Group Agent.
- **Concurrency**: `dispatch_sub_agents` must have a concurrency limit (e.g., max 10 sub-agents at once) to avoid API rate limits and memory exhaustion.
- **Timeouts**: Sub-Agents must have strict execution timeouts. If a database is unreachable, the Sub-Agent should report "Timeout" rather than hanging the entire Group RCA process.