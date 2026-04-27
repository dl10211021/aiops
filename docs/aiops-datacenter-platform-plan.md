# AIOps Datacenter Platform Implementation Plan

## Overview

目标是把当前系统从“多协议聊天执行工具”升级为“面向运维的数据中心 AIOps 平台”。平台以资产中心为核心，资产类型、登录协议、工具集、巡检、告警、任务、报表和未来大屏都由后端统一目录和接口驱动，前端只消费后端配置，不再硬编码资产类型或工具入口。

## Current Baseline

已完成的 Phase 0：

- 扩展基础资产目录到 OS、数据库、容器、K8s、中间件、网络、虚拟化、存储、监控、带外和安全类资产。
- 新增后端工具集入口：K8s、容器运行时、中间件、存储、监控、虚拟化。
- 新增资产 CRUD 基础接口：`POST /assets`、`GET /assets/{id}`、`PUT /assets/{id}`、`DELETE /assets/{id}`。
- 新增大屏预留接口：`GET /dashboard/overview`、`GET /dashboard/toolsets`。
- 新增后端 Slash Command 目录：`GET /session/{session_id}/commands`。
- 前端资产中心和连接弹窗已开始转为后端资产目录驱动。
- 新增协议化巡检模板：OS、数据库、网络、SNMP、K8s、容器、监控、虚拟化、带外等资产不再依赖散落在 skills 里的单独 Python 脚本。
- 协议验证已拆成“连接/登记、协议原生探测、工具目录、只读巡检、定时巡检”五步：Windows 走 WinRM，数据库走原生驱动，HTTP/K8s/监控走 HTTP API，SNMP 走 OID 探测，避免非 SSH 资产只做虚拟登记。
- 新增审批中心和持久化审批队列：高危工具调用由后端统一拦截、记录、审批、超时。
- 新增生产化健康检查、部署文档、备份恢复文档、发布清单、CI 和大屏入口。
- 新增工作区审计工具：区分产品代码、依赖产物、运行状态、敏感状态、构建产物，并明确暂存区/工作区状态。
- 新增提交门禁：`python scripts/worktree_audit.py --check-staged` 和 `python scripts/preflight.py --check-git` 可阻止误提交密钥、运行状态、`node_modules`、日志和构建缓存。
- 最近一次完整验证通过：后端单元测试、前端 build、安全扫描、依赖检查、预检脚本。

## Architecture Decisions

- 资产类型是业务子类型，协议是登录/执行通道，二者必须分离。例如 `k8s/k8s`、`docker/ssh`、`prometheus/http_api`、`nas/snmp`。
- 所有工具由后端 `tool_registry` 暴露，前端不得自行判断某类资产应该有哪些工具。
- 巡检能力采用模板化 CRUD，不把巡检命令散落在聊天 prompt 或前端按钮里。
- 大屏接口只返回聚合数据和趋势数据，不直接暴露资产密码、token、kubeconfig 等敏感字段。
- 高危操作继续走后端审批和安全策略，前端只负责展示和确认，不决定最终安全结果。
- 单资产验证不能只依赖连接登记成功。非 SSH 资产必须至少完成一次协议原生只读探测；探测失败时跳过深度巡检并标记该次验证失败。
- 仓库清理必须保守执行：本地资产凭据、密钥、运行数据库、审批和巡检证据不能作为普通源码改动提交。

## Phase 1: Asset Center Foundation

### Task 1.1: Asset Catalog Contract

**Description:** 稳定资产类型目录接口，让前端、大屏、导入模板、工具目录都使用同一份后端目录。

**Acceptance criteria:**
- `GET /assets/types` 返回 `categories`、`types`、默认端口、协议、巡检 profile。
- 每个资产类型都有稳定 `id/category/protocol/default_port/inspection_profile`。
- 前端连接弹窗不再依赖静态资产列表作为主数据源。

**Verification:**
- `python -W default -m unittest discover -s tests -p "test_asset_protocol_layer.py"`
- `npm run build`

**Dependencies:** None

**Files likely touched:**
- `core/asset_protocols.py`
- `api/routes.py`
- `frontend/src/components/modals/ConnectionModal.tsx`

**Estimated scope:** Medium

### Task 1.2: Asset CRUD Completion

**Description:** 补齐资产增删改查、单资产详情、批量导入、脱敏、保留原密码更新、标签和分类查询能力。

**Acceptance criteria:**
- 支持创建、修改、删除、查询单资产和列表。
- 修改资产时传 `********` 不覆盖原密码和敏感 extra_args。
- 响应永远不返回明文密码、token、kubeconfig。

**Verification:**
- 新增/更新资产 CRUD 测试。
- `python -W default -m unittest discover -s tests -p "test*.py"`

**Dependencies:** Task 1.1

**Files likely touched:**
- `core/memory.py`
- `api/routes.py`
- `frontend/src/api/client.ts`
- `tests/test_asset_crud_routes.py`

**Estimated scope:** Medium

### Checkpoint: Phase 1

- 后端测试全通过。
- 前端构建通过。
- 资产中心能按后端分类新增/编辑/保存/连接资产。

## Phase 2: Protocol Tools And Inspection Templates

### Task 2.1: Protocol Tool Routing Matrix

**Description:** 为每类资产建立协议工具路由矩阵，确保模型知道自己已经连接到当前资产，不再要求用户重复提供账号密码。

**Acceptance criteria:**
- Windows、Linux、DB、Redis、MongoDB、HTTP API、K8s、SNMP、网络 CLI、容器、中间件、存储、虚拟化都有明确工具入口。
- `/execute` legacy 路由和聊天工具路由一致。
- 工具调用强制使用资产中心托管凭据，忽略模型提供的账号密码。

**Verification:**
- `python -W default -m unittest discover -s tests -p "test_tool_catalog_routes.py"`
- `python -W default -m unittest discover -s tests -p "test_execute_route_protocols.py"`

**Dependencies:** Phase 1

**Files likely touched:**
- `core/tool_registry.py`
- `core/dispatcher.py`
- `api/routes.py`
- `tests/test_tool_catalog_routes.py`
- `tests/test_execute_route_protocols.py`

**Estimated scope:** Medium

### Task 2.2: Inspection Template CRUD

**Description:** 把巡检从硬编码命令升级为模板化能力，支持每种资产配置默认只读巡检命令/API。

**Acceptance criteria:**
- 提供巡检模板列表、新增、修改、删除、启停接口。
- 模板按资产类型和协议匹配。
- 只读模式下只执行安全模板。

**Verification:**
- 新增 `tests/test_inspection_templates.py`。
- `python -W default -m unittest discover -s tests -p "test*.py"`

**Dependencies:** Task 2.1

**Files likely touched:**
- `core/session_inspector.py`
- `core/inspection_templates.py`
- `api/routes.py`
- `frontend/src/api/client.ts`

**Estimated scope:** Medium

### Checkpoint: Phase 2

- 每类资产至少有连接测试、工具目录、基础巡检路径。
- 巡检模板 CRUD 可用。

## Phase 3: Ops Workflows, Alerts, Reports, Dashboard APIs

### Task 3.1: Scheduled Inspection CRUD

**Description:** 把现有 Cron 巡检升级为任务 CRUD，支持资产、资产组、标签、模板、通知方式。

**Acceptance criteria:**
- 支持创建、修改、暂停、恢复、删除、手动运行巡检任务。
- 任务可绑定资产 ID、标签或全局范围。
- 执行结果可查询。

**Verification:**
- 新增任务 CRUD 测试。
- 手动验证一个只读任务能创建和查询。

**Dependencies:** Phase 2

**Estimated scope:** Medium

### Task 3.2: Alert Rule And Event APIs

**Description:** 告警接入从简单 webhook 升级为事件表和规则接口。

**Acceptance criteria:**
- Webhook 入库，保留原始 payload 和标准化字段。
- 支持按资产、严重级别、状态查询告警。
- 支持认领、关闭、备注和关联 AI 会话。

**Verification:**
- 新增告警事件测试。

**Dependencies:** Phase 1

**Estimated scope:** Medium

### Task 3.3: Dashboard Data Contracts

**Description:** 为后期大屏提供稳定接口，不先做大屏 UI。

**Acceptance criteria:**
- 提供资产总览、在线率、告警趋势、巡检成功率、风险排行、资源 TopN 接口。
- 所有接口返回结构稳定、无敏感字段。

**Verification:**
- 新增 dashboard API 测试。

**Dependencies:** Task 3.1, Task 3.2

**Estimated scope:** Medium

## Phase 4: Frontend AIOps Console

状态：已完成基础控制台整改。

本轮完成内容：
- 新增 `dashboard` 运维总览视图，接入资产总览、告警趋势、风险排行和工具覆盖接口。
- 左侧导航新增“总览”，Logo 默认进入总览。
- 资产中心新增分类、协议、关键字过滤，并在卡片上显示分类、标签、协议和账号主机上下文。
- 定时巡检页升级为任务管理页，支持绑定资产、模板、范围、通知渠道、编辑、暂停、恢复、删除和立即执行。
- 定时巡检支持按资产、标签、分类、协议和类型从资产中心展开目标，并把每个目标的协议、端口、资产类型传入后台执行体。
- 新增巡检运行记录持久化和查询接口，前端巡检任务卡片展示最近运行结果。
- 范围巡检任务创建不再强制填写单台主机和用户名，真正支持按标签、分类、协议、资产类型、全部资产批量巡检。
- Dashboard 总览新增巡检成功率、目标成功数、最近失败/部分失败运行记录，供后续大屏直接复用。
- 聊天输入区新增当前资产快捷动作，直接使用后端下发的会话命令。
- 前端 API client 补齐巡检模板 CRUD、Dashboard 扩展接口、Cron 更新/暂停/恢复/立即执行接口。

### Task 4.1: Asset Center UI Completion

**Description:** 资产中心支持后端目录驱动的筛选、编辑、详情、连接、巡检测试。

**Acceptance criteria:**
- 可按分类、协议、标签、关键字筛选。
- 可打开资产详情并编辑保存。
- 巡检测试结果在资产详情中展示。

已交付补充：
- 资产验证抽屉展示按资产过滤的定时巡检运行记录。
- 资产侧巡检运行可直接打开报告详情并导出 Markdown/JSON。

**Verification:**
- `npm run build`
- 手动检查资产中心主流程。

**Dependencies:** Phase 1, Phase 2

**Estimated scope:** Medium

### Task 4.2: Chat Execution Console

**Description:** 聊天页升级为运维执行控制台，显示工具、审批、风险、巡检和资产上下文。

**Acceptance criteria:**
- Slash commands 来自后端。
- 执行轨迹可展开，显示开始、完成、耗时、结果、审批。
- 读写模式提示和后端审批链路清晰可见。

已交付补充：
- 聊天顶部显示当前资产、账号、范围、标签、技能数、活跃工具数和只读/读写风险姿态。
- 活跃会话接口返回 `target_scope` / `scope_value`，刷新后仍可保留会话范围上下文。

**Verification:**
- `npm run build`

**Dependencies:** Phase 2

**Estimated scope:** Medium

### Task 4.3: Dashboard Placeholder UI

**Description:** 为大屏预留前端入口和基础卡片，不做最终视觉大屏。

**Acceptance criteria:**
- 新增大屏/概览视图入口。
- 消费 `/dashboard/overview`。
- UI 不暴露敏感字段。

**Verification:**
- `npm run build`

**Dependencies:** Phase 3.3

**Estimated scope:** Small

## Phase 5: Verification And Hardening

状态：当前阶段回归验证已完成。

本轮验证：
- `npm run build` 通过。
- `python -W default -m unittest discover -s tests -p "test*.py"` 后端全量测试通过。
- `python scripts/security_scan.py` 通过。
- `python -m pip check` 通过。
- GitHub Actions `quality` 工作流已在 `master` 分支通过。

### Task 5.1: Full Regression Verification

**Acceptance criteria:**
- 后端全量测试通过。
- 前端构建通过。
- 安全扫描通过。
- 依赖检查通过。

**Verification:**
- `python -W default -m unittest discover -s tests -p "test*.py"`
- `npm run build`
- `python scripts/security_scan.py`
- `python -m pip check`

### Task 5.2: Residual Risk List

**Acceptance criteria:**
- 列出尚未接入深度 SDK 的厂商和当前 fallback 方式。
- 列出需要真实环境验证的协议。
- 列出生产部署前必须确认的依赖和系统驱动。

当前残留风险：
- 深度厂商 SDK 仍未全部接入：VMware/OpenStack/Proxmox/Redfish/K8s/Prometheus 等当前已有统一工具入口，但真实生产建议逐类补 SDK 级适配和集成测试。
- 真实环境验证仍不足：Windows WinRM、MySQL/PostgreSQL/Oracle/MSSQL、SNMP 网络设备、K8s、虚拟化、存储需要用实际资产做端到端巡检。
- 定时巡检已支持资产/标签/分类/协议/类型展开、结果查询、失败重试、运行耗时和成功率趋势；生产环境仍需用真实任务校准阈值和告警策略。
- 前端已有总览页和基础大屏路由；后续仍可继续增强实时告警态势、交互钻取和大屏专用视觉布局。
- 当前 `git status` 已保持干净，`frontend/node_modules`、运行时状态文件和构建策略已从索引/ignore 角度收敛；敏感密钥仍需在生产发布前轮换，并且历史提交中的旧密钥清理需要单独授权执行。

## Execution Rules

- 每次只推进一个 Task 或一个小 Checkpoint。
- 每个 Task 完成后更新 Plan 状态并说明验证结果。
- 不再把资产类型或工具列表写死在前端作为主数据源。
- 所有敏感数据新增接口必须默认脱敏。
- 高危命令即使前端确认，也必须经过后端策略判断。

## Phase 6: Real Asset E2E Verification Matrix

目标：把“真实资产端到端验证”做成平台能力，而不是靠人工临时点按钮。

### Task 6.1: Protocol Verification Matrix API

**Description:** 后端提供按资产或全量资产生成验证矩阵的接口，覆盖连接测试、会话注册、工具目录、只读巡检、定时巡检可用性。

状态：已完成基础矩阵接口和前端契约。

**Acceptance criteria:**
- 可按资产 ID 查询该资产需要验证的步骤和当前支持状态。
- 全量接口按资产类型、协议、分类汇总待验证项。
- 不返回明文密码、token、kubeconfig。

已交付：
- `GET /verification/protocols`
- `GET /assets/{asset_id}/verification`
- `core/protocol_verification.py`
- 前端 `ProtocolVerificationOverview` / `AssetVerificationMatrix` 类型和 API client 方法。

**Verification:**
- `python -W default -m unittest discover -s tests -p "test_protocol_verification_matrix.py"`
- `python -W default -m unittest discover -s tests -p "test*.py"`

**Dependencies:** Phase 1, Phase 2, Phase 3

**Files likely touched:**
- `core/protocol_verification.py`
- `api/routes.py`
- `tests/test_protocol_verification_matrix.py`
- `frontend/src/api/client.ts`
- `frontend/src/types/index.ts`

**Estimated scope:** Medium

### Task 6.2: Verification Runner

**Description:** 支持对单资产执行端到端验证，记录每一步结果，包括连接测试、会话工具、只读巡检和定时巡检 dry-run。

状态：已完成后端执行器、历史记录和前端 API 契约。

**Acceptance criteria:**
- `POST /assets/{id}/verify` 执行验证并返回步骤结果。
- 验证结果持久化，可按资产查看历史。
- 验证过程不执行读写命令。

已交付：
- `POST /assets/{asset_id}/verify`
- `GET /assets/{asset_id}/verification/runs`
- `core.protocol_verification.run_asset_verification`
- 验证步骤：连接测试、工具目录、只读巡检、定时巡检 dry-run。
- 验证历史持久化到 `protocol_verification_runs.json`，响应默认脱敏。
- 前端 `AssetVerificationRun` 类型和 `verifyAsset/getAssetVerificationRuns` API client。

**Verification:**
- 新增 runner 单元测试。
- 真实资产手动验证至少 Linux、Windows、MySQL、交换机各 1 台。

**Dependencies:** Task 6.1

**Estimated scope:** Medium

### Task 6.3: Frontend Verification UI

**Description:** 资产中心增加“验证”入口和验证矩阵视图，明确展示哪些资产已通过、失败、未验证。

状态：已完成资产中心验证入口、矩阵状态和验证历史抽屉。

**Acceptance criteria:**
- 资产卡片显示验证状态。
- 支持从资产详情触发验证。
- 失败步骤展示错误原因和下一步建议。

已交付：
- 资产中心概览展示验证就绪资产数量。
- 资产卡片展示验证矩阵覆盖度。
- 每个资产卡片增加“验证”按钮。
- 验证抽屉展示验证矩阵、可用工具、验证历史、失败/跳过步骤原因。
- 支持前端触发 `POST /assets/{asset_id}/verify` 并刷新历史。

**Verification:**
- `npm run build`
- 手动检查资产验证主流程。

**Dependencies:** Task 6.2

**Estimated scope:** Medium

## Phase 7: Inspection Report Closed Loop

### Task 7.1: Inspection Report Detail And Export

**Description:** 把巡检运行记录升级为报告，支持详情、Markdown/JSON 导出、按资产过滤。

状态：已完成后端报告详情、导出、前端 API 契约和巡检页报告查看入口。

**Acceptance criteria:**
- 巡检报告详情接口不暴露敏感字段。
- 支持 Markdown 导出。
- 前端可打开最近一次巡检报告。

已交付：
- `GET /inspection-runs`
- `GET /inspection-runs/{run_id}/report`
- `GET /inspection-runs/{run_id}/export?format=markdown|json`
- `list_runs(asset_id=...)` 支持按资产过滤目标结果。
- Markdown/JSON 报告导出默认脱敏。
- 前端 `InspectionReport` 类型和报告查询/导出 API client。
- 定时巡检页最近运行记录可打开报告详情，并导出 Markdown/JSON。
- 资产中心验证抽屉可按资产查看巡检运行，并复用报告详情弹窗。

**Verification:**
- 后端报告测试。
- `npm run build`

### Task 7.2: Retry And Duration Metrics

**Description:** 增加失败重试策略、步骤耗时、运行耗时分布和趋势接口。

状态：已完成失败重试、运行/目标耗时和 Dashboard 趋势指标。

**Acceptance criteria:**
- 可配置失败重试次数。
- 记录 run duration 和 target duration。
- Dashboard 展示耗时和失败率趋势。

已交付：
- Cron 任务新增 `retry_count`，前端任务表单可配置失败重试次数。
- 手动/定时巡检目标记录 `attempts`、`started_at`、`completed_at`、`duration_ms`。
- 巡检运行记录记录 `duration_ms`。
- 新增 `GET /dashboard/inspection-runs/trend`，按日期返回运行成功率、目标成功/失败数和平均耗时。
- Dashboard 增加巡检成功率与耗时趋势展示。

## Phase 8: Protocol Deep Adapters

### Task 8.1: K8s And Prometheus Native Templates

**Description:** 补 K8s/Prometheus 原生巡检模板和专项指标。

状态：已完成 K8s/Prometheus 内置只读巡检模板和会话级匹配。

**Acceptance criteria:**
- K8s 覆盖 node/pod/event/deployment 基础健康。
- Prometheus 覆盖 up、告警、CPU/内存/磁盘指标模板。

已交付：
- 模板层新增内置模板注册，`GET /inspection-templates` 同时返回内置和自定义模板。
- 自定义模板仍优先匹配，内置模板作为 fallback，避免覆盖用户自定义巡检。
- 内置模板标记 `builtin/source/readonly`，并禁止通过保存接口覆盖内置模板 ID。
- K8s 内置模板覆盖 nodes、pods、deployments、events。
- Prometheus 内置模板覆盖 buildinfo、targets、up、ALERTS、CPU、内存、磁盘 PromQL 查询。
- 会话巡检已验证 K8s 使用 `k8s_api_request`，Prometheus 使用 `monitoring_api_query`。

### Task 8.2: Database And Windows Deep Templates

**Description:** 补 Oracle/MSSQL/PostgreSQL/MySQL/Windows 专项巡检模板。

状态：已完成 Windows 与主流 SQL 协议内置只读深度模板。

**Acceptance criteria:**
- 数据库覆盖连接数、慢查询/锁/表空间或等价指标。
- Windows 覆盖服务、事件日志、磁盘、补丁/启动时间。

已交付：
- Windows 内置模板覆盖系统版本/启动时间、硬件资源、磁盘、异常服务、近 24 小时系统错误事件、最近补丁。
- MySQL 协议模板覆盖版本、连接数、慢查询、InnoDB 状态、库空间，适配 MySQL/TiDB/OceanBase 等走 `mysql` 协议的资产。
- PostgreSQL 协议模板覆盖版本、连接概览、库统计、活跃查询、库空间，适配 PostgreSQL/Kingbase 等走 `postgresql` 协议的资产。
- Oracle 模板覆盖版本、会话数、表空间使用率、等待事件。
- SQL Server 模板覆盖版本、会话数、等待统计、数据库文件空间。
- 会话巡检已验证 Windows 走 `winrm_execute_command` 模板，MySQL 协议子类型走 `db_execute_query` 模板。

### Task 8.3: Network And Virtualization Adapters

**Description:** 补交换机、SNMP、VMware/KVM/Redfish 深度验证和模板。

状态：已完成网络、SNMP、VMware、Proxmox、KVM、Redfish 内置只读模板。

**Acceptance criteria:**
- 网络设备覆盖版本、接口、CPU/内存、错误包、邻居。
- VMware/KVM/Redfish 覆盖主机、VM、存储、硬件健康。

已交付：
- 模板合同新增向后兼容的 `asset_types`，支持一个模板覆盖多个资产子类型，例如 switch/firewall/vpn。
- 网络 CLI 模板覆盖版本、CPU、内存、接口摘要、接口错误、LLDP 邻居。
- SNMP 模板覆盖 sysDescr、sysUpTime、ifNumber、sysName，并修复模板执行路径的 SNMPv3 `v3_auth_user` 映射。
- VMware 模板覆盖版本、主机、虚拟机、数据存储。
- Proxmox 模板覆盖版本、节点、集群资源、存储。
- KVM 模板覆盖 libvirt 主机、虚拟机、存储池、虚拟网络、宿主机磁盘。
- Redfish 模板覆盖 Service Root、Systems、Chassis、Managers。

## Phase 9: Security Approval Backoffice

### Task 9.1: Approval Queue API

**Description:** 后端审批从 SSE 临时交互升级为可查询队列和审计日志。

状态：已完成审批队列 API、持久化审计和聊天审批入队。

**Acceptance criteria:**
- 支持查询待审批、已批准、已拒绝、超时。
- 审批记录包含命中策略、操作者、时间、工具参数摘要。

已交付：
- 新增 `core/approval_queue.py`，审批请求持久化到 `approval_requests.json`。
- 新增 `GET /approvals`、`GET /approvals/{approval_id}`、`POST /approvals/{approval_id}/decision`。
- 原 `POST /session/{session_id}/approve` 兼容聊天弹窗，同时写入审批审计状态。
- 聊天触发高危工具调用时自动记录 pending 审批请求。
- 审批记录包含 tool、session、资产上下文、命中原因、脱敏参数、申请/过期/处理时间、operator、note。
- pending 超时可自动归档为 `timeout`，不会混淆为人工拒绝。

### Task 9.2: Approval And Policy UI

**Description:** 前端安全策略页增加审批中心、命中原因、硬拦截规则版本管理。

状态：已完成审批中心入口和审批/拒绝操作；安全策略编辑此前已接入。

**Acceptance criteria:**
- 可审批高危工具调用。
- 可查看策略命中原因。
- 可编辑并保存硬拦截规则。

已交付：
- 左侧导航新增 `AP` 审批中心。
- 审批中心支持 pending/approved/rejected/timeout/all 过滤、刷新、批准、拒绝和备注。
- 审批列表展示工具名、命中原因、脱敏参数、资产上下文、申请时间和处理结果。
- 前端 API client 新增 `getApprovals`、`decideApproval`。

### Task 9.3: P0 Security And Swarm Control Fixes

**Description:** 修复技能变更审批、技能迁移路径安全、Swarm 工具名错配和后台自治审批绕过。

状态：已完成首批 P0 修复。

已交付：
- `evolve_skill` 独立归类为 `skill_change`，默认必须人工审批。
- `/skills/migrate` 校验目标目录名、规范化目标路径，并要求来源目录包含 `SKILL.md`。
- Master、Heartbeat、告警注入提示统一使用真实注册工具 `dispatch_sub_agents`。
- Headless/Cron/Heartbeat/Webhook 触发的后台工具调用会先走统一安全策略；命中审批策略时写入审批队列并由系统自动拒绝，避免无人值守任务直接执行高风险动作。

### Task 9.4: Skill Lifecycle Hardening

**Description:** 将技能创建/进化从直接写文件推进到可审计、可恢复、可校验的生命周期。

状态：进行中。

已交付：
- `evolve_skill` 写入前校验 `skill_id` 与文件名，拒绝目录穿越和嵌套路径。
- 更新 `SKILL.md` 时校验 YAML frontmatter，要求 `name` 与 `skill_id` 一致，并包含 `description`。
- 覆盖已有技能文件前写入 `.versions/*.bak` 备份，文件内容通过临时文件和 `os.replace` 原子替换。
- 新增技能版本列表与回滚接口，回滚前会校验版本路径和 `SKILL.md` frontmatter，并为当前文件再次生成备份。
- 新增 `POST /skills/validate` 静态校验入口，返回 `valid/issues/warnings`，不写文件、不执行脚本，用作后续审批与测试验证的前置门。
- 创建技能时复用统一静态校验，拒绝不完整 frontmatter 与嵌套脚本路径，并通过原子写入生成初始文件。
- 将技能静态校验下沉到核心生命周期模块，`create_skill` 与 `evolve_skill` 共用同一套路径、frontmatter 与空内容校验。
- `evolve_skill` 审批记录新增技能变更摘要、内容哈希、预览和校验结果，持久化参数不再保存完整技能内容。
- 高风险工具经审批执行后会把执行状态、结果摘要和完成时间写回审批记录，审批中心可直接查看执行闭环。

## Phase 10: Productionization

### Task 10.1: Frontend Product Pages

**Description:** 补资产详情页、巡检模板 CRUD 页、告警事件处理页、报告详情页和最终大屏路由。

状态：已补最终大屏路由基础版；资产、巡检、审批、安全策略等生产页已在前序阶段接入。

已交付：
- 左侧导航新增 `TV` 大屏入口。
- 新增 `BigScreen` 视图，复用 dashboard 数据合同。
- 大屏展示资产总数、在线会话、巡检成功率、待处理告警、资产分类、协议分布、告警趋势、巡检健康度、风险主机排行。
- 大屏每 60 秒自动刷新，并保留手动刷新按钮。

### Task 10.2: Deployment And Dependency Governance

**Description:** 补 `.env.example`、依赖锁定、数据库迁移、日志轮转、备份恢复、Docker/systemd 部署说明。

状态：已完成生产配置、健康检查、部署文档、备份恢复文档和 CI 质量门禁。

已交付：
- 新增 `.env.example`，覆盖 API token、CORS、LLM provider、embedding、运行目录等生产关键项。
- 新增 `GET /healthz`，返回结构化健康状态，覆盖 database、cron store、storage、frontend、hydrate。
- Dockerfile 健康检查改为 `/healthz`。
- 新增 `docs/deployment-production.md`，覆盖直接运行、Docker、systemd、验证和 rollback。
- 新增 `docs/backup-restore.md`，列出 SQLite、密钥、模型配置、审批记录、巡检记录、知识库和长期记忆备份/恢复步骤。
- 新增 `docs/release-checklist.md`，覆盖发布前检查、冒烟测试、rollback 和发布后观察。
- 新增 `.github/workflows/ci.yml`，执行后端测试、安全扫描、`pip check`、前端构建。

### Task 10.3: Worktree Cleanup

**Description:** 清理历史脏文件、node_modules 删除记录、构建产物策略和敏感文件状态。

状态：已完成非破坏性审计、ignore 收敛、历史跟踪产物移出索引、CI 门禁修复和清理说明；当前主分支工作区保持干净。

**Acceptance criteria:**
- `git status` 只剩本次计划内变更或明确保留项。
- 不误删用户数据。
- 敏感文件不进入版本库。

已交付：
- 新增 `scripts/worktree_audit.py`，只读分类当前 worktree 状态，不执行删除、reset 或索引修改。
- 新增 `tests/test_worktree_hygiene.py`，覆盖敏感状态、node_modules、日志和产品变更分类。
- 新增 `docs/worktree-cleanup.md`，定义清理策略、分类、风险项和 rollback。
- `.gitignore` 补充 `approval_requests.json`、`inspection_runs.json`、`inspection_templates.json`、`verification_runs.json`、`backups/`、`logs/`、`.git_log_frontend.txt`、`frontend/.vite/`。
- 已停止跟踪 `frontend/node_modules`、运行时数据库/JSON、日志和本地密钥等不应入库文件。
- CI 已覆盖 `master` 分支，并通过后端全量测试、安全扫描、`pip check` 和前端构建。
- 当前审计摘要：无 staged/unstaged/untracked 产品变更。
- 高风险项：`.fernet.key` 已不在最新树中，但旧提交仍包含历史密钥；生产发布前必须轮换密钥。若要从 Git 历史彻底清除，需要单独执行历史重写和强制推送流程。
