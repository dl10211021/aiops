# Observability AI Troubleshooting Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an OpsCore `可观测性` module under the existing session entry that models business systems across mixed infrastructure, binds assets/sessions/observability sources, and drives AI multi-agent troubleshooting with evidence and root-cause candidates.

**Architecture:** The module is platform-neutral and workload-pack driven. Core code owns business-system profiles, components, relationships, bindings, sources, investigations, evidence, and orchestration; specific technologies such as ZStack, VMware, physical servers, K8s, Oracle, MySQL, PostgreSQL, MongoDB, TiDB, big data, MPP databases, switches, security tools, and Prometheus are represented by profile packs and observable-source adapters rather than hard-coded into the core model.

**Tech Stack:** FastAPI route modules mounted through `api/routes.py`, Python services under `core/observability/`, SQLite-backed persistence following existing OpsCore patterns, React/Vite frontend under `frontend/src/`, existing session/asset/dispatcher/multi-agent capabilities, and targeted Python/frontend tests.

---

## Product Positioning

The new module is not a generic monitoring dashboard and must not be named or shaped as a ZStack, Oracle, or Prometheus feature. It is the business-system observability and AI troubleshooting workroom:

```text
业务系统画像
+ 工作负载画像包
+ 观测源适配
+ 资产/会话绑定
+ 多 Agent 联动排查
+ 证据链
+ 根因候选排序
```

The first visible entry should be placed directly below `会话` in the left navigation:

```text
总览
会话
可观测性
资产
画板
巡检
告警
审批
Skills
知识库
配置
```

## Design Principles

- Platform-neutral: ZStack, VMware, physical machines, K8s, bare OS, storage, network devices, and cloud resources are infrastructure profile packs.
- Database-neutral: MySQL, PostgreSQL, MongoDB, TiDB, Oracle, SQL Server, Redis, Elasticsearch, MPP, distributed SQL, and big data stores are workload profile packs.
- Unknown-friendly: missing architecture information is represented as `unknown` nodes and relationships, not as empty state or blocking validation.
- Evidence-driven: every AI-inferred component, relationship, root-cause candidate, or action recommendation must be tied to user input, metrics, logs, commands, alerts, API results, or manual confirmation.
- Session-first: existing OpsCore sessions are operational channels. Prometheus sessions can become observable sources; SSH, DB, K8s, and API sessions can become investigation channels.
- Extensible by packs: adding a new technology should usually add a profile pack, source adapter, metric mapping, and playbook, not change core profile storage.

## Non-Goals For First Release

- Do not build a full replacement for Prometheus, Grafana, Zabbix, ELK, or SkyWalking.
- Do not require a complete CMDB before the module is usable.
- Do not hard-code ZStack as the default platform.
- Do not hard-code Oracle or Oracle ERP as the primary application model.
- Do not implement destructive or auto-remediation actions in V1.
- Do not attempt to support every product-specific metric on day one.

## Core User Flows

### Flow 1: Create A Business System With Partial Knowledge

The user creates `集团global协作门户 / 测试环境` and adds only the known items:

```text
registry 测试环境
k8s-master 测试环境
k8s-worker 测试环境
k8s-worker 测试环境
中间件服务器 测试环境
Prometheus 会话
```

The system stores known components and explicitly shows unknowns:

```text
入口: unknown
应用服务: unknown
OS: unknown for each server until discovered
虚拟化/物理平台: unknown until bound to ZStack/VMware/physical
交换机/VLAN/端口: unknown until discovered or entered
数据库: unknown until discovered or entered
日志/安全/流量源: unknown or not connected
```

### Flow 2: Promote An Existing Prometheus Session

The user already has a Prometheus connection under sessions. The module lets the user register it as:

```text
source_type: prometheus
source_origin: session
capabilities:
  - query_metrics
  - query_alerts
  - discover_targets
  - query_promql
  - map_exporter_to_component
```

The source can bind to a business system, a component, or all targets discovered from Prometheus labels.

### Flow 3: AI Profile Discovery

The user starts a discovery run. The system reads known assets, sessions, Prometheus targets, and existing metadata, then proposes candidate components and relationships:

```text
candidate: k8s-worker-1 belongs to K8s cluster global-test
evidence: kube-state-metrics target labels and node exporter host label
confidence: inferred
status: pending_review
actions: confirm / reject / postpone
```

### Flow 4: AI Troubleshooting Incident

The user creates an investigation: `global门户慢了`, time window `last 2 hours`. The system generates a plan from the business profile and active profile packs:

```text
Prometheus Agent: query metrics and alerts
OS Agent: inspect CPU, memory, disk, IO, network, process state
K8s Agent: inspect pods, events, service, ingress, restarts, throttling
Database Agent: inspect DB-specific symptoms if database component is known
Middleware Agent: inspect middleware-specific health
Network Agent: inspect switch/SNMP/NetFlow if available
Security Agent: inspect antivirus/EDR/SIEM if available
Summary Agent: correlate evidence, timeline, changes, and root-cause candidates
```

## Domain Model

### Business System

Purpose: represents a business-facing system, not a server or monitor target.

Fields:

```text
id
name
environment
description
criticality
owner
aliases
tags
status
profile_completeness
created_at
updated_at
```

Examples:

```text
集团global协作门户 / 测试环境
Oracle ERP / 生产环境
数据中台 / 生产环境
营销MPP分析库 / 测试环境
```

### Component

Purpose: represents anything that can participate in a business-system topology.

Core fields:

```text
id
system_id
name
component_type
workload_family
profile_pack_id
environment
status
confidence
source
metadata_json
created_at
updated_at
```

Important component types:

```text
business_entry
application_service
batch_job
api_gateway
load_balancer
dns_record
k8s_cluster
k8s_namespace
k8s_workload
k8s_pod
k8s_service
container_registry
os_host
vm
physical_server
hypervisor_host
cloud_cluster
network_switch
router
firewall
vlan
switch_port
storage_pool
datastore
san
database_system
database_cluster
database_instance
database_node
database_endpoint
database_shard
database_replica
database_partition
middleware
message_queue
cache
bigdata_cluster
bigdata_job
mpp_cluster
security_tool
observable_source
unknown
```

### Relationship

Purpose: stores topology and dependency edges.

Fields:

```text
id
system_id
from_component_id
to_component_id
relationship_type
confidence
source
evidence_id
status
metadata_json
created_at
updated_at
```

Relationship types:

```text
runs_on
has_os
deployed_to
hosted_on
managed_by
connected_to
attached_to_network
routes_through
exposes_service_via
pulls_image_from
uses_database
uses_middleware
uses_storage
uses_datastore
uses_shared_storage
uses_interconnect
replicates_to
depends_on
observed_by
logs_to
traces_to
protected_by
queried_through_session
discovered_from
inferred_from
```

Relationship statuses:

```text
confirmed
discovered
inferred
unknown
pending_review
rejected
```

### Observable Source

Purpose: represents an external source of operational evidence. A source may be backed by an existing session.

Fields:

```text
id
name
source_type
source_origin
session_id
endpoint
capabilities_json
auth_ref
status
last_checked_at
metadata_json
created_at
updated_at
```

Source types:

```text
prometheus
zabbix
grafana
loki
elk
skywalking
pinpoint
jaeger
zstack
vmware_vcenter
k8s_api
ssh_command
database_connection
snmp
netflow
sflow
ndr
edr
antivirus
siem
cmdb
itsm
custom_http_api
```

Capabilities:

```text
query_metrics
query_logs
query_alerts
query_traces
discover_targets
discover_topology
query_changes
query_security_events
query_network_flows
run_readonly_check
query_promql
map_exporter_to_component
```

### Investigation

Purpose: represents one troubleshooting event.

Fields:

```text
id
system_id
title
symptom
time_window_start
time_window_end
severity
status
created_by
summary
created_at
updated_at
```

Investigation task fields:

```text
id
investigation_id
agent_role
target_component_id
source_id
task_type
status
input_json
output_summary
started_at
finished_at
error_message
```

Evidence fields:

```text
id
investigation_id
task_id
component_id
source_id
evidence_type
title
summary
raw_ref
raw_excerpt
confidence
timestamp
created_at
```

Root-cause candidate fields:

```text
id
investigation_id
title
description
likelihood
impact
confidence
supporting_evidence_ids
contradicting_evidence_ids
recommended_next_steps
status
created_at
updated_at
```

## Profile Pack Model

Profile packs describe technology-specific topology, metrics, logs, discovery rules, and playbooks. Core services load packs and use them without hard-coding product behavior.

Profile pack fields:

```text
id
name
workload_family
version
component_types
relationship_types
discovery_rules
metric_mappings
log_patterns
health_checks
investigation_playbooks
default_unknown_nodes
```

### Workload Families

```text
infrastructure
virtualization
physical
network
container
os
database
distributed_database
mpp_database
bigdata
middleware
application
security
observability
storage
```

### Initial Profile Packs

Start with compact, useful packs:

```text
infra_os
infra_physical_server
infra_network_device
infra_virtualization_generic
infra_zstack
infra_vmware
container_k8s
database_generic
database_mysql
database_postgresql
database_mongodb
database_tidb
database_oracle
database_redis
database_elasticsearch
mpp_generic
mpp_clickhouse
mpp_doris
mpp_starrocks
mpp_greenplum
bigdata_generic
bigdata_hadoop
bigdata_spark
bigdata_flink
bigdata_kafka
middleware_generic
security_generic
observability_prometheus
```

Do not implement full deep support for every pack in V1. V1 should include the model, loader, UI display, and small useful defaults for generic packs plus Prometheus mapping.

## Frontend Information Architecture

### Main Observability View

Route/view: `可观测性`

Tabs:

```text
业务系统
画像发现
排查事件
观测源
画像包
```

### Business System List

Purpose: show all business systems and their readiness for AI troubleshooting.

Columns:

```text
业务系统
环境
重要性
组件数
未知节点
待确认关系
绑定资产
绑定会话
观测源
最近排查
画像完整度
操作
```

Actions:

```text
查看画像
AI发现
发起排查
编辑
```

### Business System Profile

Sections:

```text
顶部身份栏: name, environment, criticality, owner, completeness, last updated
左侧组件树: grouped by layer and workload family
中间分层拓扑: business, entry, app, container, OS, infra, network, DB, big data, middleware, security, observability
右侧详情面板: selected node, bindings, evidence, status, actions
底部时间线: discovery, confirmation, investigation, alert, change events
```

### Layered Topology

Display layers:

```text
业务系统层
入口层
应用层
容器/K8s层
操作系统层
虚拟化/云平台层
物理基础设施层
网络层
数据库层
大数据/MPP层
中间件层
观测/安全层
```

Each node chip must show:

```text
component name
type
status
confidence
bound asset count
bound session count
source/evidence badge
```

Unknown nodes must be visible, not hidden.

### Observable Sources

Purpose: show all evidence sources, including existing sessions promoted into sources.

Columns:

```text
名称
类型
来源
能力
绑定业务系统
绑定组件
状态
最近检查
操作
```

Prometheus source detail should show:

```text
endpoint or session
capabilities
known labels
target count
exporter hints
linked systems/components
```

### Investigation Center

Purpose: manage troubleshooting events.

List fields:

```text
事件
业务系统
症状
时间窗口
状态
参与Agent
证据数
根因候选
创建时间
```

Detail layout:

```text
顶部: symptom, affected system, time window, severity, status
左侧: agent task plan and progress
中间: topology heat map and event timeline
右侧: root-cause candidates and next steps
底部: evidence table with source, tool, timestamp, summary, raw reference
```

## API Design

Prefix all endpoints under:

```text
/api/v1/observability
```

Initial endpoints:

```text
GET    /systems
POST   /systems
GET    /systems/{system_id}
PUT    /systems/{system_id}
DELETE /systems/{system_id}

GET    /systems/{system_id}/components
POST   /systems/{system_id}/components
PUT    /systems/{system_id}/components/{component_id}
DELETE /systems/{system_id}/components/{component_id}

GET    /systems/{system_id}/relationships
POST   /systems/{system_id}/relationships
PUT    /systems/{system_id}/relationships/{relationship_id}
DELETE /systems/{system_id}/relationships/{relationship_id}

GET    /systems/{system_id}/topology
GET    /systems/{system_id}/bindings
POST   /systems/{system_id}/bindings/assets
POST   /systems/{system_id}/bindings/sessions

GET    /sources
POST   /sources
POST   /sources/from-session
GET    /sources/{source_id}
PUT    /sources/{source_id}
POST   /sources/{source_id}/check

GET    /profile-packs
GET    /profile-packs/{pack_id}

POST   /systems/{system_id}/discovery-runs
GET    /discovery-runs/{run_id}
POST   /relationship-review-items/{item_id}/confirm
POST   /relationship-review-items/{item_id}/reject

GET    /investigations
POST   /investigations
GET    /investigations/{investigation_id}
POST   /investigations/{investigation_id}/plan
POST   /investigations/{investigation_id}/dispatch
GET    /investigations/{investigation_id}/evidence
GET    /investigations/{investigation_id}/root-causes
```

## File Map

### Backend

Create:

```text
api/observability_routes.py
core/observability/__init__.py
core/observability/models.py
core/observability/store.py
core/observability/profile_service.py
core/observability/topology_service.py
core/observability/binding_service.py
core/observability/source_registry.py
core/observability/discovery_service.py
core/observability/investigation_service.py
core/observability/evidence_service.py
core/observability/agent_orchestrator.py
core/observability/profile_packs/__init__.py
core/observability/profile_packs/base.py
core/observability/profile_packs/builtin.py
```

Modify:

```text
api/routes.py
core/tool_registry.py
core/dispatcher_session_tools.py
```

`api/routes.py` should only mount the router. Do not put observability business logic there.

### Frontend

Create:

```text
frontend/src/views/Observability.tsx
frontend/src/features/observability/api.ts
frontend/src/features/observability/types.ts
frontend/src/features/observability/BusinessSystemList.tsx
frontend/src/features/observability/BusinessSystemProfile.tsx
frontend/src/features/observability/LayeredTopology.tsx
frontend/src/features/observability/ComponentBindings.tsx
frontend/src/features/observability/ObservableSources.tsx
frontend/src/features/observability/ProfileDiscovery.tsx
frontend/src/features/observability/InvestigationCenter.tsx
frontend/src/features/observability/InvestigationDetail.tsx
```

Modify:

```text
frontend/src/App.tsx
frontend/src/components/layout/LeftNav.tsx
```

### Tests

Create:

```text
tests/test_observability_models.py
tests/test_observability_store.py
tests/test_observability_profile_service.py
tests/test_observability_topology_service.py
tests/test_observability_bindings.py
tests/test_observability_sources.py
tests/test_observability_profile_packs.py
tests/test_observability_investigation.py
tests/test_observability_routes.py
```

## Implementation Tasks

### Task 1: Add Observability Navigation And Empty Shell

**Files:**

- Create: `frontend/src/views/Observability.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/LeftNav.tsx`

- [ ] Add a `可观测性` nav item directly below `会话`.
- [ ] Register the new frontend view in the existing app shell.
- [ ] Build an empty first screen with tabs: `业务系统`, `画像发现`, `排查事件`, `观测源`, `画像包`.
- [ ] Keep visible UI Chinese-first.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observability navigation shell`.

Acceptance:

```text
The left navigation shows 可观测性 below 会话.
The page loads without backend dependency.
The current app build succeeds.
```

### Task 2: Add Core Models And Validation

**Files:**

- Create: `core/observability/__init__.py`
- Create: `core/observability/models.py`
- Create: `tests/test_observability_models.py`

- [ ] Define dataclasses or Pydantic-compatible structures for business systems, components, relationships, sources, investigations, tasks, evidence, and root-cause candidates.
- [ ] Define allowed component types, relationship types, source capabilities, confidence values, and statuses.
- [ ] Add validation for unknown-friendly profiles: missing DB, OS, network, or platform data must be valid.
- [ ] Add tests for creating a partial business system profile.
- [ ] Add tests for rejecting invalid relationship endpoints.
- [ ] Run `python -m pytest tests/test_observability_models.py -v`.
- [ ] Commit with `feat: add observability domain models`.

Acceptance:

```text
Models allow partial architecture.
Models do not assume ZStack, Oracle, or Prometheus.
Unknown nodes and pending-review relationships are valid states.
```

### Task 3: Add SQLite Store

**Files:**

- Create: `core/observability/store.py`
- Create: `tests/test_observability_store.py`

- [ ] Inspect existing SQLite store conventions in the repo before implementation.
- [ ] Create tables for systems, components, relationships, bindings, sources, profile packs, discovery runs, investigations, tasks, evidence, and root-cause candidates.
- [ ] Implement idempotent table initialization.
- [ ] Implement CRUD primitives with JSON metadata fields.
- [ ] Add tests using a temporary repo-local SQLite database.
- [ ] Run `python -m pytest tests/test_observability_store.py -v`.
- [ ] Commit with `feat: persist observability profiles`.

Acceptance:

```text
Store initialization can run repeatedly.
CRUD operations work in isolation.
JSON metadata is preserved.
Tests do not write to production opscore.db.
```

### Task 4: Add Business System Profile Service

**Files:**

- Create: `core/observability/profile_service.py`
- Create: `tests/test_observability_profile_service.py`

- [ ] Implement create/list/get/update/delete for business systems.
- [ ] Calculate `profile_completeness` from confirmed components, unknown nodes, source bindings, and pending-review relationships.
- [ ] Add helper to bootstrap a partial profile from user-provided system name, environment, and known components.
- [ ] Add tests using `集团global协作门户 / 测试环境` with registry, k8s-master, two workers, middleware, and unknown DB/network/OS.
- [ ] Run `python -m pytest tests/test_observability_profile_service.py -v`.
- [ ] Commit with `feat: manage business system profiles`.

Acceptance:

```text
The service creates useful partial profiles.
Profile completeness is deterministic.
Known and unknown architecture can coexist.
```

### Task 5: Add Components, Relationships, And Layered Topology

**Files:**

- Create: `core/observability/topology_service.py`
- Create: `tests/test_observability_topology_service.py`

- [ ] Implement component CRUD operations through the profile service or topology service.
- [ ] Implement relationship CRUD operations.
- [ ] Implement layered topology output grouped by business, entry, app, container, OS, virtualization, physical, network, database, big data, MPP, middleware, security, and observability layers.
- [ ] Implement unknown-node creation helpers.
- [ ] Add tests for ZStack, VMware, physical machine, K8s, database, big data, MPP, switch, and security nodes all represented through the same model.
- [ ] Run `python -m pytest tests/test_observability_topology_service.py -v`.
- [ ] Commit with `feat: build layered observability topology`.

Acceptance:

```text
Topology output is layer-based, not product-based.
ZStack and VMware are sibling infrastructure nodes.
MySQL, PG, Mongo, TiDB, Oracle, MPP, and big data are represented through workload families.
Unknown switch, OS, database, or storage nodes can be shown.
```

### Task 6: Add Asset And Session Binding

**Files:**

- Create: `core/observability/binding_service.py`
- Create: `tests/test_observability_bindings.py`

- [ ] Implement component-to-asset binding.
- [ ] Implement component-to-session binding.
- [ ] Implement business-system-to-session binding.
- [ ] Add relation `queried_through_session`.
- [ ] Add tests that bind registry/k8s/middleware components to existing-style asset/session ids.
- [ ] Add tests that bind a Prometheus session as a source candidate.
- [ ] Run `python -m pytest tests/test_observability_bindings.py -v`.
- [ ] Commit with `feat: bind observability profiles to assets and sessions`.

Acceptance:

```text
Components can point to assets and sessions without duplicating asset-center data.
Sessions are treated as operational channels.
Bindings survive reload through the store.
```

### Task 7: Add Observable Source Registry

**Files:**

- Create: `core/observability/source_registry.py`
- Create: `tests/test_observability_sources.py`

- [ ] Implement source CRUD.
- [ ] Implement `create_source_from_session(session_id, source_type, capabilities)`.
- [ ] Implement Prometheus source defaults: `query_metrics`, `query_alerts`, `discover_targets`, `query_promql`, `map_exporter_to_component`.
- [ ] Implement source binding to system and component.
- [ ] Add tests for registering an existing Prometheus session as an observable source.
- [ ] Add tests for future source types: SNMP, VMware, ZStack, ELK, EDR, NDR, DB connection.
- [ ] Run `python -m pytest tests/test_observability_sources.py -v`.
- [ ] Commit with `feat: register observability sources`.

Acceptance:

```text
Existing Prometheus sessions can become observable sources.
Source capability checks are data-driven.
The design supports future logs, traces, network, security, and platform APIs.
```

### Task 8: Add Profile Pack Loader

**Files:**

- Create: `core/observability/profile_packs/base.py`
- Create: `core/observability/profile_packs/builtin.py`
- Create: `tests/test_observability_profile_packs.py`

- [ ] Define the profile pack schema.
- [ ] Register generic built-in packs for OS, physical server, network device, virtualization, K8s, database, distributed database, MPP, big data, middleware, security, and Prometheus.
- [ ] Add compact product-specific packs for MySQL, PostgreSQL, MongoDB, TiDB, Oracle, Redis, ClickHouse, Doris, StarRocks, Greenplum, Hadoop, Spark, Flink, Kafka, VMware, and ZStack.
- [ ] Keep product-specific packs declarative in V1.
- [ ] Add tests that ensure all built-in packs load and have required fields.
- [ ] Run `python -m pytest tests/test_observability_profile_packs.py -v`.
- [ ] Commit with `feat: add workload profile packs`.

Acceptance:

```text
Adding a new database or platform does not require core model changes.
Initial packs describe components, relationships, metrics, and investigation hints.
```

### Task 9: Add Observability API Routes

**Files:**

- Create: `api/observability_routes.py`
- Modify: `api/routes.py`
- Create: `tests/test_observability_routes.py`

- [ ] Implement system CRUD endpoints.
- [ ] Implement component and relationship endpoints.
- [ ] Implement topology endpoint.
- [ ] Implement binding endpoints.
- [ ] Implement source endpoints including `from-session`.
- [ ] Implement profile-pack listing endpoint.
- [ ] Mount the router in `api/routes.py`.
- [ ] Add route tests using FastAPI test client or the repo's existing API test pattern.
- [ ] Run `python -m pytest tests/test_observability_routes.py -v`.
- [ ] Commit with `feat: expose observability api`.

Acceptance:

```text
/api/v1/observability endpoints work.
api/routes.py only mounts the route.
Route tests do not require live Prometheus, SSH, or database systems.
```

### Task 10: Build Business System List UI

**Files:**

- Create: `frontend/src/features/observability/api.ts`
- Create: `frontend/src/features/observability/types.ts`
- Create: `frontend/src/features/observability/BusinessSystemList.tsx`
- Modify: `frontend/src/views/Observability.tsx`

- [ ] Implement API client functions for systems and profile packs.
- [ ] Implement business system list table.
- [ ] Add create/edit minimal form.
- [ ] Show profile completeness, component count, unknown count, pending review count, bound sessions, and observable sources.
- [ ] Add actions: `查看画像`, `AI发现`, `发起排查`.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observability business system list`.

Acceptance:

```text
The UI can create and list business systems.
Empty and loading states are useful.
Chinese labels are used in visible UI.
```

### Task 11: Build Profile Detail And Layered Topology UI

**Files:**

- Create: `frontend/src/features/observability/BusinessSystemProfile.tsx`
- Create: `frontend/src/features/observability/LayeredTopology.tsx`
- Create: `frontend/src/features/observability/ComponentBindings.tsx`
- Modify: `frontend/src/views/Observability.tsx`

- [ ] Implement system detail view.
- [ ] Render layered topology grouped by layer.
- [ ] Render unknown nodes with clear status.
- [ ] Render component detail panel with asset/session/source bindings.
- [ ] Add manual component and relationship creation.
- [ ] Add binding UI for assets and sessions.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observability profile topology`.

Acceptance:

```text
The user can see incomplete architecture without losing context.
Unknown OS, DB, switch, storage, or platform nodes are visible.
Bindings are visible per component.
```

### Task 12: Build Observable Sources UI

**Files:**

- Create: `frontend/src/features/observability/ObservableSources.tsx`
- Modify: `frontend/src/views/Observability.tsx`

- [ ] Implement sources list.
- [ ] Add `从会话登记观测源` action.
- [ ] Add Prometheus source type preset.
- [ ] Show source capabilities.
- [ ] Show bound business systems and components.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observable sources ui`.

Acceptance:

```text
The user can promote an existing Prometheus session to an observable source.
The UI does not require Prometheus to be queried in V1.
```

### Task 13: Add AI Profile Discovery Skeleton

**Files:**

- Create: `core/observability/discovery_service.py`
- Create: `frontend/src/features/observability/ProfileDiscovery.tsx`
- Modify: `api/observability_routes.py`
- Create or extend: `tests/test_observability_profile_service.py`

- [ ] Implement discovery run creation.
- [ ] Implement rule-based discovery inputs from known systems, assets, sessions, and source metadata.
- [ ] Generate relationship review items.
- [ ] Add confirm/reject operations for review items.
- [ ] Add UI to show discovery progress and pending relationship proposals.
- [ ] Add tests that AI-inferred relationships do not become confirmed until accepted.
- [ ] Run related pytest tests.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observability profile discovery`.

Acceptance:

```text
Discovery can propose relationships from partial data.
All inferred relationships require review before becoming confirmed.
Rejected proposals are preserved as audit history.
```

### Task 14: Add Investigation And Evidence Services

**Files:**

- Create: `core/observability/investigation_service.py`
- Create: `core/observability/evidence_service.py`
- Create: `tests/test_observability_investigation.py`
- Modify: `api/observability_routes.py`

- [ ] Implement investigation CRUD.
- [ ] Implement investigation task creation.
- [ ] Implement evidence append/list.
- [ ] Implement root-cause candidate append/list.
- [ ] Implement a deterministic investigation plan builder from system topology and profile packs.
- [ ] Add tests for creating an investigation from symptom `系统慢`.
- [ ] Add tests for storing evidence and root-cause candidates.
- [ ] Run `python -m pytest tests/test_observability_investigation.py -v`.
- [ ] Commit with `feat: manage observability investigations`.

Acceptance:

```text
An investigation can be created without live external systems.
Evidence is first-class and queryable.
Root-cause candidates reference evidence.
```

### Task 15: Add Multi-Agent Orchestration Integration

**Files:**

- Create: `core/observability/agent_orchestrator.py`
- Modify: `core/tool_registry.py`
- Modify: `core/dispatcher_session_tools.py`
- Extend: `tests/test_observability_investigation.py`

- [ ] Inspect existing multi-agent tools before adding new ones.
- [ ] Add tool metadata for reading a business-system profile.
- [ ] Add tool metadata for creating or updating investigation evidence.
- [ ] Add tool metadata for dispatching investigation tasks to available sessions.
- [ ] Implement orchestration that creates task records before dispatch and stores results as evidence after completion.
- [ ] Add guardrails: V1 tasks must be read-only unless explicitly approved through existing approval flow.
- [ ] Add tests for task creation and evidence capture with stubbed dispatch.
- [ ] Run related tests.
- [ ] Commit with `feat: orchestrate observability investigation agents`.

Acceptance:

```text
The module can plan multi-agent work.
Agent outputs become evidence.
No destructive operation is introduced by default.
```

### Task 16: Build Investigation Center UI

**Files:**

- Create: `frontend/src/features/observability/InvestigationCenter.tsx`
- Create: `frontend/src/features/observability/InvestigationDetail.tsx`
- Modify: `frontend/src/views/Observability.tsx`

- [ ] Implement investigation list.
- [ ] Implement create-investigation form with business system, symptom, severity, and time window.
- [ ] Implement detail view with agent tasks, topology context, evidence table, and root-cause candidates.
- [ ] Add dispatch button that calls the backend orchestration endpoint.
- [ ] Render pending, running, completed, and failed states.
- [ ] Run `npm run build`.
- [ ] Commit with `feat: add observability investigation ui`.

Acceptance:

```text
The user can create a troubleshooting event from the UI.
The detail page shows task plan, evidence, and root-cause candidates.
```

### Task 17: Integrate Existing Alerts, Inspections, And Canvas

**Files:**

- Modify: `core/observability/evidence_service.py`
- Modify: `api/observability_routes.py`
- Potentially modify existing alert/inspection/canvas service files after impact review.

- [ ] Inspect existing alert, inspection, and realtime canvas routes/services.
- [ ] Add linking from alerts to business systems when component or source bindings match.
- [ ] Add ability to attach inspection results as investigation evidence.
- [ ] Add ability to create or reference realtime canvas views from investigation detail.
- [ ] Keep integrations narrow and avoid changing existing alert behavior unless covered by tests.
- [ ] Add targeted tests for each integration.
- [ ] Run affected tests.
- [ ] Commit with `feat: connect observability to alerts inspections and canvas`.

Acceptance:

```text
Existing alert/inspection/canvas data can support observability investigations.
Existing behavior remains compatible.
```

### Task 18: Verification And Release Gate

**Files:**

- No new files unless fixing issues.

- [ ] Run targeted backend tests:

```powershell
python -m pytest tests/test_observability_models.py tests/test_observability_store.py tests/test_observability_profile_service.py tests/test_observability_topology_service.py tests/test_observability_bindings.py tests/test_observability_sources.py tests/test_observability_profile_packs.py tests/test_observability_investigation.py tests/test_observability_routes.py -v
```

- [ ] Run frontend build:

```powershell
npm run build
```

- [ ] Run repo preflight:

```powershell
python scripts/preflight.py --check-git
```

- [ ] Before committing final batch, check staged files:

```powershell
python scripts/worktree_audit.py --check-staged
```

- [ ] Commit final fixes with an appropriate message.

Acceptance:

```text
All targeted tests pass.
Frontend build passes.
Preflight does not report unexpected dirty/generated/sensitive files.
No files under .research/hermes-agent are edited or staged.
```

## First Release Scope

V1 should stop at a useful product slice:

```text
1. Left navigation entry under 会话
2. Business system list and profile detail
3. Components, relationships, unknown nodes
4. Asset and session bindings
5. Prometheus session promoted as observable source
6. Built-in profile pack registry
7. AI discovery proposals with manual confirmation
8. Manual investigation creation
9. Multi-agent task plan skeleton
10. Evidence and root-cause candidate storage/display
```

V1 should not require real ZStack, VMware, Oracle, MySQL, PG, Mongo, TiDB, Hadoop, switch, EDR, or NDR integrations to be available. It must be useful with partial data and existing sessions.

## Future Scope

After V1:

```text
1. Prometheus PromQL execution and exporter-to-component mapping
2. Zabbix and ELK/Loki source adapters
3. K8s API discovery adapter
4. VMware vCenter and ZStack API discovery adapters
5. SNMP/LLDP/NetFlow network discovery
6. Database-specific deep checks for MySQL, PostgreSQL, MongoDB, TiDB, Oracle, Redis, ES
7. Big data and MPP-specific playbooks
8. Security source adapters for antivirus, EDR, SIEM, NDR
9. Change-event correlation
10. SLO and business-impact modeling
11. Similar-incident retrieval
12. Postmortem generation
13. Approval-gated remediation
```

## Success Criteria

The first usable version is successful when the user can:

```text
1. Open 可观测性 from below 会话.
2. Create 集团global协作门户 / 测试环境.
3. Add known registry, k8s-master, k8s-worker, middleware components.
4. Leave OS, DB, switch, storage, platform, and entry nodes unknown.
5. Bind components to assets and sessions.
6. Promote an existing Prometheus session into an observable source.
7. See the partial layered topology.
8. Run AI profile discovery and review proposed relationships.
9. Create a "系统慢" investigation.
10. See agent tasks, evidence, and root-cause candidates in one detail page.
```

## Implementation Notes

- Keep `.research/hermes-agent/` out of scope.
- Keep route logic thin; put business logic under `core/observability/`.
- Keep visible UI Chinese-first.
- Prefer additive APIs and isolated services.
- Do not block on complete infrastructure knowledge.
- Do not turn unknown architecture into validation errors.
- Treat all external-system checks as read-only in V1.
- Preserve existing sessions, alerts, inspections, and canvas behavior.
