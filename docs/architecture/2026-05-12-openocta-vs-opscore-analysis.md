# OpenOcta 与 OpsCore 全面对比分析

日期：2026-05-12

范围：

- OpenOcta 源码：`.research/openocta`
- OpsCore 源码：当前仓库 `D:\AIOPS\skillops - 20260225`
- 本报告基于源码、文档、路由、前端页面、GitNexus 索引和本地文件枚举；未启动 OpenOcta 做运行时体验测试。
- OpenOcta 为 GPLv3 项目，建议只吸收产品/架构设计，不直接复制代码到 OpsCore。

## 1. 总体定位

| 维度 | OpenOcta | OpsCore 当前项目 | 判断 |
|---|---|---|---|
| 产品定位 | 通用企业 AI Agent 控制平面 | 面向真实运维的 AIOps 平台 | 方向不同，不能简单替换 |
| 第一对象 | Agent、会话、通道、Cron、Skills、MCP | 资产、会话、协议工具、巡检、审批、知识、可观测 | OpsCore 更贴近运维现场 |
| 部署目标 | 单 Go 二进制 + 内嵌前端 + 桌面/服务形态 | Python/FastAPI + React/Vite，开发迭代快 | OpenOcta 部署形态更成熟 |
| 外部入口 | WebSocket Gateway、HTTP、Webhook、IM Channel、CLI | REST API、SSE Chat、WebSocket Terminal、部分 Webhook | OpenOcta 控制面协议更统一 |
| 运维深度 | 泛 Agent，可接 MCP/Channels | 深资产、深协议、深巡检、深审批 | OpsCore 核心优势明显 |

结论：

- OpenOcta 最值得学的是“控制平面工程化”：统一 Gateway、通道运行时、数字员工、Trace、配置 Schema、单包部署。
- OpsCore 最不能丢的是“运维业务闭环”：资产中心、协议原生验证、只读巡检、报告、通知、审批、可观测、多系统排查。
- 最优路线不是合并 OpenOcta，而是在 OpsCore 里吸收它的控制面能力，并改造成 AIOps 语义。

## 2. 代码规模与入口

| 项 | OpenOcta | OpsCore |
|---|---|---|
| 后端语言 | Go 1.25 | Python 3.11 |
| 前端技术 | Lit + Vite | React 19 + TypeScript + Vite + Tailwind |
| 后端入口 | `src/cmd/openocta`，`gateway run`，`agent -m`，`node` | `main.py`，FastAPI app，`/api/v1` |
| 前端入口 | `ui/src/main.ts`，生产内嵌到 Go | `frontend/src/App.tsx`，构建到 `static_react/` |
| 索引规模 | 未用 GitNexus 索引 | GitNexus：1037 文件，20397 符号，300 执行流 |
| API 数量 | WebSocket 方法 109 个，HTTP 路由约 44 个 | FastAPI 路由 179 个 |
| 页面数量 | 顶层/兼容 Tab 约 29 个 | 主视图 13 个，另有多个弹窗/子视图 |

## 3. 部署、打包、运行形态

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 单二进制 | Go build 后一个 `openocta`，内含前端和配置模板 | 需要 Python 环境 + requirements + 前端构建产物 | OpenOcta 更好 |
| 前端内嵌 | `go:embed` 内嵌 `src/embed/frontend` | FastAPI 服务 React 静态目录 | OpenOcta 分发更简单 |
| CLI | `openocta gateway run/status/health/call/install/stop/restart`，`agent`，`node` | 主要 `python main.py` 和脚本 | OpenOcta CLI 更完整 |
| 桌面应用 | Wails、Windows/macOS 桌面壳、DMG/MSI 计划 | Web 为主，预留桌面端，当前无桌面壳 | OpenOcta 更成熟 |
| Linux 服务 | systemd、GoReleaser、deb/rpm 设计 | 有生产部署文档和 CI，但服务安装弱一些 | OpenOcta 包装更完整 |
| Docker | `deploy/Dockerfile` + Makefile docker | 未见同等一键 Docker 主路径 | OpenOcta 更好 |
| 运行模式 | desktop/service，决定监听地址 | 默认本地 Uvicorn/服务 | OpenOcta 更细 |
| 单实例保护 | appinstance 可杀掉其它实例，支持跳过 | OpsCore 无同类显式机制 | OpenOcta 更好 |
| 环境变量文档 | 独立 `environment-variables.md` | `.env.example` + 配置中心 | OpenOcta 文档更全 |

建议：

- OpsCore 不必改 Go，但应做“一键启动包 / Docker Compose / Windows 服务”。
- 前端继续 React；部署上可用 PyInstaller/Nuitka、Docker、Windows service 或内置静态目录，不需要照搬 Wails。

## 4. Gateway、API 与通信协议

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| WebSocket Gateway | `/ws`，req/res/event，hello features，connect.challenge | 主要 REST + Chat SSE + Terminal WS | OpenOcta 更统一 |
| 方法注册 | `handlers.NewRegistry` 方法名映射到 handler | FastAPI route modules | 各有优势 |
| 方法发现 | hello 返回 methods/events | API docs 可看 REST，但前端无统一方法发现 | OpenOcta 更好 |
| 事件推送 | `agent/chat/presence/tick/health/cron/node/device/approval` 等事件 | Chat SSE、session polling、终端 WS | OpenOcta 系统级事件更好 |
| HTTP API | health、config、upload、desktop、site proxy、hooks、pprof | 179 个 AIOps REST route | OpsCore 业务 API 更强 |
| Debug/pprof | Go pprof 暴露 | Python 无同类内置页面 | OpenOcta 更好 |
| API 结构 | Gateway 方法偏平台控制 | 路由按业务域拆分：asset/session/inspection/knowledge 等 | OpsCore 业务边界更好 |
| 对外 hook | `/hooks/wake`、`/hooks/agent`、`/hooks/alert` | `/webhook/alert`、session webhook | OpenOcta Hook 更系统 |

OpenOcta WebSocket 方法覆盖：

- health/status/logs
- channels/status/logout/QR
- usage/cost
- tts
- config/env/schema/patch/set/apply
- exec approvals
- wizard/talk mode
- models
- agents/agent files
- employees
- skills/install/update/delete/file edit
- sessions/list/create/ensure/preview/patch/reset/delete/compact/usage
- trace/list/content
- approval list/approve/deny/whitelist
- heartbeat/wake
- node/device pairing
- send/agent/chat
- cron/list/status/add/remove/update/run/runs

OpsCore REST API 覆盖：

- chat、attachments
- assets、asset groups、normalize、batch import
- connections、execute、disconnect
- sessions runtime/history/profile/webhook
- tools catalog/center/session tools
- skills registry/create/validate/rollback/migrate
- approvals and execution
- dashboard
- alerts and alert webhook
- notifications
- cron inspection jobs/runs/templates/reports
- protocol verification
- knowledge/RAG/memory/vault
- realtime canvas
- observability
- config/model/provider/safety/retention/embedding
- system info

建议：

- OpsCore 可以保留 REST，但新增一个“运行事件总线”：巡检进度、通知结果、工具事件、会话状态统一推送，减少轮询和弹窗卡死。

## 5. 前端导航与页面功能

| 页面/能力 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 总览 | Overview | Dashboard/BigScreen | OpsCore 更运维化 |
| 消息/聊天 | Message/Chat | 会话主工作台 | OpsCore 更深 |
| 会话管理 | Sessions | Session Sidebar + history/profile/export | OpsCore 更强 |
| 定时任务 | ScheduledTasks/Cron/CronHistory | 巡检 | OpenOcta 调度通用，OpsCore 巡检业务强 |
| 数字员工 | DigitalEmployee/EmployeeMarket | 无独立页面，有 agent profile/skills/session | OpenOcta 更好 |
| Skill | SkillLibrary/Skills | SkillMarket、创建、验证、回滚、迁移 | OpsCore 更偏自进化 |
| Tool | ToolLibrary | ToolCenter | OpsCore 工具更运维化 |
| 模型 | ModelLibrary/Models | 模型配置弹窗 | OpenOcta 展示更完整，OpsCore 配置更实用 |
| MCP | MCP 页面 | 无独立 MCP 页面 | OpenOcta 更好 |
| Channels | Channels | 通知配置弹窗 | OpenOcta 更好 |
| Logs | Logs | 无完整日志视图 | OpenOcta 更好 |
| LLM Trace | LLM Trace | 会话工具 trace，但无 LLM Trace 中心 | OpenOcta 更好 |
| Sandbox/Security | Sandbox/Security | SafetyPolicyModal + ApprovalCenter | OpsCore 策略更贴运维 |
| 资产 | 无 CMDB | AssetVault | OpsCore 独有优势 |
| 可观测 | 无业务拓扑中心 | ObservabilityCenter | OpsCore 独有优势 |
| 知识库 | Memory/Skills 为主 | KnowledgeBase/RAG/Memory/Vault | OpsCore 更强 |
| 画板 | 无 | RealtimeCanvas | OpsCore 独有优势 |
| 告警 | Hook alert | AlertCenter + Dashboard trend | OpsCore 更贴运维 |

OpsCore 页面清单：

- 总览、大屏、会话、可观测性、资产、画板、巡检、告警、审批、Skills、工具、知识库、配置。
- 弹窗：连接、模型配置、通知配置、会话保留、安全策略、动态 Skills、会话操作。

OpenOcta 页面清单：

- message、scheduledTasks、cronHistory、employeeMarket、skillLibrary、toolLibrary、modelLibrary、tutorials、aboutUs、community、agents、overview、channels、instances、sessions、usage、cron、skills、mcp、nodes、chat、digitalEmployee、config、envVars、models、debug、logs、llmTrace、sandbox。

建议：

- OpsCore 不需要照搬 OpenOcta 的市场/社区/教程入口。
- 应吸收 OpenOcta 的 Logs、LLM Trace、MCP、Channel 页面能力。

## 6. 会话与聊天工作台

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 会话 key | `agent:main:*`、employee、cron、alert 等稳定 key | session_id 绑定资产、协议、用户、技能、状态 | OpsCore 更贴资产 |
| 聊天发送 | `chat.send`，支持队列、abort、inject | `/chat` SSE 流，工具事件、审批、交互 | OpsCore 更运维化 |
| 附件 | 图片/文件、粘贴图片、预览 | attachments preview、上传解析、消息附件 | 两边都有 |
| 模型选择 | chat modelRef + session thinking/reasoning | ModelSelector、ThinkingModeSelector、模型配置 | 两边都有 |
| 上下文压缩 | session compact、compaction indicator | session retention、history limit、memory 活动 | OpenOcta UI 提示更好 |
| 会话侧栏 | 搜索、重命名、分享链接、删除 | 分组、重命名、标签、备注、搜索、同步后端 | OpsCore 更强 |
| 批量删除 | Sessions 页面支持 | session sidebar/历史能力较分散 | OpenOcta 更直接 |
| 工具轨迹 | conversationOnly 可隐藏/显示工具行 | ToolTraceList、工具证据、策略按钮、错误摘要 | OpsCore 更强 |
| 审批卡片 | approval queue | ToolApprovalCard、ApprovalCenter、决策弹窗 | OpsCore 更强 |
| 用户交互 | askuserquestion | UserInteractionCard/clarify/request_user_interaction | 两边都有，OpsCore 更结合会话 |
| 终端 | 无明显资产终端 | SessionTerminalModal、xterm、SSH 终端镜像 | OpsCore 独有 |
| 快捷命令 | 简单 prompt | 大量协议感知 slash commands、自定义命令管理 | OpsCore 更强 |
| 资产画像 | 无 | AssetProfilePanel、relation、focus、evidence | OpsCore 独有 |
| 思考链 | compaction/trace | AiThinkingChainPanel | OpsCore 更强 |
| 会话反馈 | 未见同等业务反馈 | 点赞/点踩、记忆策略、反馈追踪 | OpsCore 更强 |

建议：

- OpsCore 应补“会话级运行总览”：LLM 调用、工具调用、审批、记忆、通知、耗时统一串成时间线。
- OpenOcta 的“分享链接、批量删除、compact 指示器”可以作为小功能吸收。

## 7. 资产中心与协议接入

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 资产中心 | 无真实 CMDB/资产库 | AssetVault saved assets | OpsCore 明显更强 |
| 资产分类 | 无 | 操作系统、数据库、容器、网络、存储、监控、安全、AI、CI/CD 等 | OpsCore 更强 |
| 资产分组 | 无 | groups bulk/rename/delete | OpsCore 更强 |
| 批量导入 | 无 | `/assets/batch_import` | OpsCore 更强 |
| 资产归一化 | 无 | normalize preview/apply | OpsCore 更强 |
| 类型表单 | 无 | form catalog、protocol-specific parameters | OpsCore 更强 |
| 连接测试 | 无资产级 | `/connect/test`、`/assets/{id}/verify` | OpsCore 更强 |
| 协议验证记录 | 无 | protocol verification runs | OpsCore 更强 |
| 凭据保留 | OpenOcta 通道/配置 secrets | OpsCore masked secret、资产编辑保持密码 | OpsCore 贴资产 |

OpsCore 当前协议/资产覆盖：

- 主机：Linux/Unix/AIX SSH、Windows WinRM、Hyper-V。
- 数据库：Oracle、MySQL/TiDB/OceanBase/MariaDB、PostgreSQL/Kingbase/openGauss/Greenplum/Vastbase、SQL Server、DB2、达梦、虚谷、Hive、IoTDB。
- 缓存/文档：Redis、Memcached、MongoDB。
- HTTP 数据平台：ClickHouse、Elasticsearch、NebulaGraph、Doris、StarRocks、HBase、HugeGraph、InfluxDB 等。
- 容器：Kubernetes、Docker、containerd、podman、Harbor。
- 中间件：Nginx、Tomcat、Kafka、RabbitMQ、RocketMQ、Zookeeper、Nacos、Consul。
- 虚拟化/云：VMware、OpenStack、Proxmox、Hyper-V、ZStack、KVM。
- 网络：交换机、路由、防火墙、VPN、F5、A10、WAF、DNS、SNMP。
- 存储：S3、MinIO、Ceph、NAS/SAN/NFS、HDFS、GlusterFS、备份平台。
- 监控：Prometheus、Alertmanager、Grafana、Loki、VictoriaMetrics、Zabbix、HertzBeat、ManageEngine。
- 服务探测：HTTP、TLS、WebSocket、TCP/UDP、ICMP、FTP、SMTP、POP3、IMAP、MQTT、NTP、Modbus、S7、Registry、IPMI、LDAP、JMX、Kafka。
- 安全身份：堡垒机、LDAP/AD、审计平台。
- AI/CI/CD：AI 平台、GPU、Jenkins/GitLab/ArgoCD 等方向预留。

建议：

- 资产中心是 OpsCore 的核心护城河，不应弱化成 OpenOcta 的 Agent/Channel 配置。
- OpenOcta 的“数字员工/角色”应该绑定到 OpsCore 资产类型、协议和巡检模板上。

## 8. 工具系统、Tool Center 与 Dispatcher

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 工具来源 | agentsdk-go builtin + OpenOcta gateway tools + MCP | OpsCore ToolRegistry + dispatcher families + Hermes controlled tools | OpsCore 业务工具更强 |
| 内置通用工具 | bash、file、grep、glob、webfetch、websearch、task、ask user | browser/web/vision/image/todo/clarify/utility 等，另有 Hermes 工具 | 两边都有 |
| 运维协议工具 | 主要靠 MCP/通用 bash | linux/winrm/network/db/redis/mongo/http/k8s/monitoring/storage/snmp 等 | OpsCore 更强 |
| 工具目录 | tool library | ToolCenter 按 toolset 展示 | OpsCore 更贴场景 |
| 工具上下文 | Agent/MCP context | session/asset/protocol context | OpsCore 更强 |
| 工具执行 | ToolExecutor + GatewayInvoker | SkillDispatcher.route_and_execute + tool family modules | OpsCore 更细 |
| 工具安全 | sandbox/validator/approval | safety_policy、read-only、approval、hard block、network boundary | OpsCore 更贴运维 |
| 工具证据 | Trace/JSONL | ToolEvidence、ExecTraceItem、结果摘要 | OpsCore 更强 |
| MCP | 一等公民，stdio/url/service | 目前不是一等 UI | OpenOcta 更好 |
| 工具文件编辑 | skills file edit、files.read | skill evolution、本地脚本限制、rollback | OpsCore 更安全 |

OpsCore 工具族：

- 资产会话：Linux、Windows、Network CLI、Container、Middleware、Storage。
- 数据：SQL、Redis、Memcached、MongoDB。
- 平台 API：HTTP、database API、bigdata API、middleware API、discovery API、container API、network API、security API、CI/CD API、AI platform API、OOB API、Kubernetes、monitoring、virtualization、storage、service probe、SNMP。
- 平台能力：memory、knowledge、skills、session search、todo、clarify、vision、image、browser、web、messaging、controlled Hermes。

建议：

- 补 MCP 页面和 MCP 服务配置，但不要让 MCP 取代已有协议原生工具。
- Tool Center 增加“谁能用、什么资产启用、是否只读、是否需审批、最近失败原因、测试入口”。

## 9. Skills 与技能演进

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| Skill 格式 | `SKILL.md`，目录或单文件 | `SKILL.md`，内置/自定义/市场/演进 | 两边一致 |
| 加载来源 | extraDirs、bundled、managed、workspace，优先级清晰 | skills、my_custom_skills、market display、active skills | OpenOcta 来源层级更清楚 |
| Skill 安装 | upload/install/update/delete | create/validate/rollback/migrate/scan | OpsCore 演进更强 |
| Skill 文件编辑 | listFiles/getFile/saveFile | custom_skill storage/version/rollback | OpsCore 更安全 |
| 依赖检查 | bins/env/config/os | 有技能验证，但依赖模型不如 OpenOcta 文档化 | OpenOcta 可借鉴 |
| 数字员工专属技能 | employee_skills | 没有角色专属技能目录 | OpenOcta 更好 |
| 技能市场 | skill library/site proxy | SkillMarket，偏本地/自定义 | OpenOcta 市场化更强 |

建议：

- 保留 OpsCore 技能演进为核心。
- 吸收 OpenOcta 的“角色专属 skills”和“依赖声明/可用性检查”。

## 10. 数字员工 / 专家角色

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 数字员工列表 | employees.list/get/create/delete | 无独立专家页 | OpenOcta 更好 |
| 人设 Prompt | manifest prompt | agent_profile 和会话 prompt | OpenOcta 更清晰 |
| 专属 MCP | manifest.mcpServers 覆盖全局 | 无专属 MCP | OpenOcta 更好 |
| 专属 Skills | employee_skills | session active_skills | OpenOcta 更好 |
| 启用/禁用 | enabled flag | 无专家级启停 | OpenOcta 更好 |
| 复制员工 | UI 有 copy | 无 | OpenOcta 更好 |
| 员工会话 | `agent:main:employee:<id>` | session 绑定资产/技能 | 各有方向 |
| 删除联动会话 | 删除员工可删关联会话 | 无专家会话关联 | OpenOcta 更完整 |

OpsCore 应改造成：

- Oracle 巡检专家
- Linux SRE 专家
- 网络设备专家
- K8s 专家
- 数据库性能专家
- 存储/备份专家
- 告警分析专家
- 可观测总控专家

不是照搬“员工市场”，而是做“运维专家包”：角色 + 资产类型 + 工具白名单 + Skills + MCP + 巡检模板 + 安全策略。

## 11. Cron、定时任务、巡检与报告

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 调度类型 | `at/every/cron`，支持时区 | 5 段 cron | OpenOcta 更灵活 |
| 任务目标 | main/isolated session，agent turn/system event | asset/all/tag/category/protocol/type | OpsCore 更贴运维 |
| 数字员工绑定 | 支持 `digitalEmployeeId` | 无 | OpenOcta 更好 |
| 执行负载 | systemEvent / agentTurn | AI 巡检 prompt + 资产会话 | OpsCore 更贴巡检 |
| 运行日志 | 每任务 JSONL runs/jobId.jsonl | `inspection_runs.json`，保留 1000 条 | OpenOcta 存储形态更好 |
| 手动运行 | cron.run force 新 session | `/cron/{job_id}/run`，运行中拦截 | 两边都有 |
| 停用/启用 | enabled/toggle | pause/resume | 两边都有 |
| 删除任务 | cron.remove | delete job | 两边都有 |
| 运行历史 | CronHistory | CronRunHistory + report modal | OpsCore 报告更强 |
| 取消运行 | 未见完整取消 | cancel current run | OpsCore 更好 |
| 重试 | 未见目标级 retry | retry_count | OpsCore 更好 |
| 超时 | Agent run timeout/env | 按协议：默认 10 分钟，数据库 20，Oracle 30，可配置 | OpsCore 更贴巡检 |
| 通知 | delivery none/announce/webhook/channel | notification_channel auto/wechat/dingtalk/email | OpenOcta delivery 抽象更通用，OpsCore 实际巡检通知更贴业务 |
| 报告导出 | cron summary/log | report/export markdown/delete | OpsCore 更好 |
| 多目标 | 通用 job 不面向资产 | resolve_targets 支持范围 | OpsCore 更强 |

OpsCore 当前已做好的巡检点：

- 新建巡检计划从资产中心选择资产。
- 可选模板、通知渠道、主动 Skills。
- 支持立即执行、暂停/恢复、删除计划。
- 支持运行中检测、取消当前巡检、轮询刷新。
- 支持报告弹窗、报告删除、报告导出。
- 支持失败/部分成功/取消/空目标状态。
- 支持企业微信/钉钉/邮件通知。

OpsCore 还不如 OpenOcta 的地方：

- 调度表达不如 `at/every/cron + timezone` 易用。
- 运行日志存储不如 JSONL/SQLite 适合长期增长。
- 进度事件不够实时，前端仍靠轮询和 busy 状态。
- 通知结果没有作为一等运行事件展示。
- 缺数字员工/专家绑定。

建议：

- 保留“巡检”作为业务页面。
- 底层抽象 JobRunEvent：queued/running/target_start/tool_call/target_done/notification/report_written/cancelled。
- 任务计划支持简单周期、指定时间、Cron 三种模式。
- 报告区做折叠列表、批量删除、按资产/状态/时间筛选。

## 12. 通知、Channel 与 IM 接入

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| Channel 抽象 | ChannelPlugin、RuntimeChannel、OutboundAdapter、ChannelManager | `send_notification` 函数 + 配置 | OpenOcta 更好 |
| 入站消息 | WeWork/Feishu/DingTalk 可触发 Agent | 主要无入站 IM | OpenOcta 更好 |
| 出站消息 | send/chat.send/outbound registry/runtime send | wechat/dingtalk/email webhook/SMTP | OpenOcta 更通用 |
| 企业微信 | 智能机器人 WebSocket，接收/发送 Markdown，QR start/poll | 群机器人 webhook | OpenOcta 更强 |
| 微信 | weixin runtime/QR | 无 | OpenOcta 更好 |
| 飞书 | WebSocket runtime、@ 触发、Markdown 卡片、图片 | 无 | OpenOcta 更好 |
| 钉钉 | Stream runtime、DM/group、Markdown | Webhook 发送 | OpenOcta 更强 |
| QQ | 已注册 runtime | 无 | OpenOcta 更好 |
| Slack/Telegram/Discord/WhatsApp | 代码有骨架，注册暂注释 | 无 | OpenOcta 有扩展基础 |
| 通道状态 | configured/running/connected/lastInbound/error/account | 通知配置 test | OpenOcta 更好 |
| 多账号 | channel account snapshots | 无 | OpenOcta 更好 |
| 允许列表 | allowedIds/group mention | 无 | OpenOcta 更安全 |

建议：

- OpsCore 应把当前通知配置升级为“通道中心”：
  - 出站：企业微信、钉钉、邮件先稳定。
  - 状态：配置、测试、最近发送、最近错误、失败重试。
  - 后续入站：企业微信里查巡检报告、触发巡检、查资产。
- 企业微信建议保留 webhook 作为轻量出口，再增加智能机器人模式作为高级入口。

## 13. 告警与可观测

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 告警 Hook | `/hooks/alert` 标准化告警 prompt | `/webhook/alert` + AlertCenter | OpsCore 更业务化 |
| 告警列表 | 无完整告警中心 | AlertCenter、AlertDetail、状态 patch | OpsCore 更好 |
| 告警趋势 | usage/overview 侧重控制面 | dashboard alerts trend | OpsCore 更好 |
| 可观测源 | MCP/Prometheus 能接 | ObservableSources | OpsCore 更好 |
| 业务系统画像 | 无 | Systems/profile/components/unknowns/sources | OpsCore 独有 |
| 画像发现 | 无 | discovery candidates | OpsCore 独有 |
| 排查任务 | hook agent/session | investigations/tasks/evidence/root causes | OpsCore 更强 |
| Profile packs | 无 | profile packs | OpsCore 更强 |
| 资产/会话绑定业务系统 | 无 | bind assets/sessions | OpsCore 更强 |
| 多 Agent 总控 | 数字员工/agent 可模拟 | Observability Master Agent UI 雏形 | OpsCore 方向更对 |

建议：

- OpenOcta 的 `/hooks/agent` 和 `/hooks/alert` 模式可以借鉴：外部事件进来后生成隔离会话，并向主会话写摘要。
- OpsCore 可观测页面继续走业务画像，不要退回通用监控面板。

## 14. 知识库、记忆与 RAG

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| Session store | 有 session store/transcript/preview/usage | 有 session history/message store/export | 两边都有 |
| Memory | `pkg/memory` 有 manager/store/search/sync 框架 | file memory、LanceDB/RAG、knowledge vault、session memory activity | OpsCore 更强 |
| RAG 文档 | 未见完整知识库 UI | 上传、列表、预览、reindex、向量状态、删除 | OpsCore 更强 |
| 记忆治理 | 数字员工/skills 上下文 | pending/review/quality/version/redact/restore/export | OpsCore 更强 |
| 知识金库 | 无 | candidates/articles/search/graph/import/export/approve | OpsCore 独有 |
| 会话反馈入记忆 | 未见同等 | up/down feedback、memory policy | OpsCore 更强 |

建议：

- OpenOcta 在这块不值得照搬。
- OpsCore 应增加 Trace 与报告对知识库的安全沉淀：成功巡检经验、失败原因、修复动作可进入会话记忆或知识候选。

## 15. 安全、审批与执行边界

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| API Token | gateway token/password/device | X-API-Key/Bearer | 两边都有 |
| 设备身份 | ed25519 device identity、pair/token rotate/revoke | 无 | OpenOcta 更好 |
| 节点配对 | node pair/list/verify/rename/invoke | 无 | OpenOcta 更好 |
| Sandbox | allowedPaths、networkAllow、resourceLimit | 网络边界、安全策略，但无通用沙箱层 | OpenOcta 更系统 |
| Validator | banCommands/banArguments/banFragments/maxLength | 动作语义分类、只读拦截、硬拦截 | OpsCore 更贴运维 |
| Approval Queue | approve/deny/whitelistSession/TTL | approval request/decision/execute/session approvals | OpsCore 更业务化 |
| 权限规则 | .claude/settings permissions allow/ask/deny | safety_policy action rules/categories/platform/scope | OpsCore 更细 |
| 只读模式 | 通用 sandbox/permissions | allow_modifications false 时针对命令/SQL/API 拦截 | OpsCore 更强 |
| 网络边界 | sandbox networkAllow | safety_network_boundary | 两边都有 |
| 审批超时 | timeoutSeconds | approval_timeout_seconds | 两边都有 |
| 审计证据 | trace/logs | ToolEvidence、Approval execution | OpsCore 更贴运维 |

建议：

- OpsCore 不应直接替换为 OpenOcta 的安全模型。
- 可吸收三层命名和 UI：Sandbox / Validator / Approval Queue，让用户理解更简单。
- 增加“会话白名单 TTL”可借鉴，但必须绑定资产、工具、动作类型，不能泛放行。

## 16. 模型、配置与环境变量

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| Provider catalog | 内置 20+ provider，`provider/model` | 默认 Google/Anthropic/DeepSeek/Ollama，可自定义 provider | OpenOcta catalog 更全 |
| 模型引用格式 | `provider/modelId` | `provider|model` | 各自可用，OpenOcta 更接近公共格式 |
| 模型 UI | ModelLibrary、Models、provider logos | LLMConfigModal，主/辅助模型、自动拉取模型 | OpsCore 更实用 |
| 动态拉模型 | 文档主要靠 provider/env | OpenAI-compatible refresh models | OpsCore 更符合用户要求 |
| Config schema | config.schema、config patch、JSON schema | 各配置路由和弹窗 | OpenOcta 更统一 |
| Env vars UI | envVars 页面 | 通知/模型等分散配置 | OpenOcta 更好 |
| 安全配置 | security config | safety policy | OpsCore 更业务化 |
| 会话保留 | 未见同等 UI | session retention | OpsCore 更强 |

建议：

- 扩展 OpsCore 默认 Provider catalog，但仍以“真实拉取到的模型”为准。
- 新增配置导入/导出、差异预览、敏感字段遮蔽。

## 17. 日志、Trace、Debug、Usage

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 日志查看 | `logs.tail` + Logs 页面 | logging service，但无完整日志页面 | OpenOcta 更好 |
| LLM Trace | JSONL + HTML，trace.list/content | 工具 trace 有，模型请求 trace 无集中页面 | OpenOcta 更好 |
| Usage | usage.status/cost，sessions.usage/timeseries/logs | dashboard metrics、session metrics | OpenOcta 用量更系统 |
| Debug 方法调用 | Debug 页面可 call method | FastAPI docs + 无 Debug UI | OpenOcta 更好 |
| pprof | Go pprof | 无 | OpenOcta 更好 |
| 工具错误摘要 | 基础 Trace | ToolErrorSummary、DatabaseResultSummary、PolicyBlockedSummary | OpsCore 更贴工具 |
| 运行事件 | cron/event | 巡检记录但事件粒度不足 | OpenOcta 思路更好 |

建议：

- OpsCore 优先补“AI Trace 中心”：
  - 模型请求/响应摘要
  - 工具调用
  - 审批
  - 资产/会话上下文
  - 巡检 target 进度
  - 通知发送结果
  - 报告写入

## 18. 实时画板与可视化

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 实时指标画板 | 无 | RealtimeCanvas | OpsCore 独有 |
| 指标采集 | 通用 Agent/MCP | session-based script/metrics/topology/fault story | OpsCore 更强 |
| HTML 导出 | 无 | `/realtime-canvas/{id}/export.html` | OpsCore 更强 |
| 自动延展 | 无 | extend | OpsCore 更强 |
| 停止/过期 | 无 | stop/expired/remaining | OpsCore 更强 |

建议：

- 画板可接入 OpenOcta 的 Trace 思路：画板中的每次采集、命令、错误、生成 HTML 都成为可审计事件。

## 19. 市场、远程站点与生态入口

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 员工市场 | employeeMarket + site API | 无 | OpenOcta 更好 |
| 技能库 | skillLibrary + site API | SkillMarket 本地/自定义 | OpenOcta 市场化更强 |
| 工具库 | toolLibrary | ToolCenter | OpsCore 工具实用，OpenOcta 包装更市场化 |
| 模型库 | modelLibrary | 模型配置 | OpenOcta 展示更强 |
| 教程 | tutorials | 文档为主 | OpenOcta 更好 |
| 社区/关于 | community/aboutUs | 无 | OpenOcta 更产品化 |
| 安装接口 | `/api/v1/install` | 无 | OpenOcta 更好 |

建议：

- OpsCore 当前阶段不必做社区和教程。
- 可做“专家包/巡检包/工具包”的本地导入和私有市场，服务于 AIOps，不做泛市场。

## 20. 桌面、节点、设备、TTS、浏览器

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| Desktop uninstall | 有 API | 无 | OpenOcta 更好 |
| Clear workspace | 有 API | 无 | OpenOcta 更好 |
| Open URL | 有 API | 无 | OpenOcta 更好 |
| Device pair/token | 有 | 无 | OpenOcta 更好 |
| Node pair/invoke | 有 | 无 | OpenOcta 更好 |
| TTS | status/providers/enable/disable/convert/setProvider | Hermes TTS 工具标签，但无完整产品页 | OpenOcta 更好 |
| Browser request | `browser.request` stub/handler | Hermes browser tools、browser toolset | OpsCore 工具层更实际 |
| Voice wake | voicewake get/set | 无 | OpenOcta 有但对 OpsCore 价值低 |

建议：

- 桌面/设备/节点能力不是当前 OpsCore 最高优先级。
- 若未来要“多节点执行器/边缘采集器”，OpenOcta 的 node pairing 可以参考。

## 21. 数据存储与运行文件

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 状态目录 | `~/.openocta` / `%APPDATA%\openocta` | 仓库内多 runtime 文件 + `.env` | OpenOcta 状态目录更清晰 |
| 配置文件 | `openocta.json` / JSON5 | `.env`、providers.json、safety_policy.json 等 | OpenOcta 更统一 |
| Cron store | JSON jobs + runs JSONL | `cron_jobs.sqlite` + `inspection_runs.json` | OpsCore 调度存 SQLite，报告 JSON 需优化 |
| Session store | file store/transcripts | active sessions + history store | 两边都有 |
| Skills store | bundled/managed/workspace/employee skills | skills/my_custom_skills | 两边都有 |
| Runtime artifacts | `.trace`、logs、workspace | LanceDB、inspection_runs、protocol runs、approval json、logs | OpsCore 更复杂，需要治理 |

建议：

- OpsCore 应把运行态数据统一迁移到明确 state dir，避免仓库根目录越来越多运行文件。
- 巡检报告和 Trace 建议 SQLite/JSONL 分表存储，保留索引。

## 22. 测试、CI 与质量门禁

| 小功能 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| 前端测试 | Vitest + browser Playwright | 当前 package 只有 build/preview/dev | OpenOcta 更好 |
| 后端测试 | Go tests | pytest/unittest 测试较多 | OpsCore 更强 |
| CI | 未见 `.github/workflows`，有 Makefile/Goreleaser | GitHub Actions `scripts/preflight.py --check-git` | OpsCore 更好 |
| Preflight | Makefile build/snapshot | preflight、worktree_audit、security_scan | OpsCore 更强 |
| Secret/runtime audit | 未见同等脚本 | worktree_audit/preflight | OpsCore 更好 |
| 浏览器验证 | Playwright dev deps | 可用但项目脚本少 | OpenOcta 前端测试配置更好 |

建议：

- OpsCore 前端补最小 Vitest/Playwright smoke，尤其巡检页面、会话、资产编辑、通知配置。
- 保留 preflight/worktree_audit，这是 OpsCore 工程优势。

## 23. 文档完整度

| 文档主题 | OpenOcta | OpsCore | 对比 |
|---|---|---|---|
| README | 完整介绍、构建、配置 | 有项目 README/agent.md | 两边都有 |
| 架构 | `architecture.md` | `agent.md`、docs/architecture | 两边都有 |
| 配置 | configuration/env/model/security/MCP/channel docs | 多数在代码/agent.md/配置 UI | OpenOcta 更系统 |
| 安全 | security/security-quickstart/redesign/permission settings | SafetyPolicy 代码/UI，文档较少 | OpenOcta 文档更好 |
| Channels | overview/config/extending | 通知配置较少文档 | OpenOcta 更好 |
| Desktop | desktop design | 无 | OpenOcta 更好 |
| 运维业务 | 泛 Agent 文档 | 资产/巡检/可观测代码强，文档需补 | OpsCore 代码强，文档弱 |

建议：

- OpsCore 需要把“资产 -> 会话 -> 工具 -> 巡检 -> 报告 -> 通知 -> 知识沉淀”的工作流写成正式文档。

## 24. 哪些可以直接借鉴为 OpsCore 功能

高优先级：

1. AI Trace 中心：借鉴 OpenOcta LLM Trace，但扩展为 AIOps Run Trace。
2. 通道中心：借鉴 ChannelPlugin/RuntimeChannel/OutboundAdapter。
3. 运维专家包：借鉴数字员工，改造成资产/协议/巡检绑定的专家角色。
4. 通用 Job 底座：借鉴 `at/every/cron/timezone/delivery/run log`。
5. 配置 Schema/Env UI：借鉴 config.schema/envVars。
6. 日志页面：借鉴 logs.tail。
7. 会话 compact/分享链接/批量删除等小体验。

中优先级：

1. MCP 一等配置页面。
2. 会话白名单 TTL 审批。
3. Device/Node pairing，为未来多执行节点准备。
4. 远程市场变体：私有专家包/巡检包市场。

低优先级：

1. TTS/voice wake。
2. 社区/about/tutorials 页面。
3. Wails 桌面壳。
4. pprof 等 Go 特有能力。

## 25. 哪些 OpsCore 已经比 OpenOcta 做得好

- 资产中心和协议建模。
- 多类数据库、主机、网络、存储、监控、虚拟化、服务探测接入。
- 协议原生工具暴露给 AI。
- 只读巡检、模板、目标范围、报告、取消、重试、导出、删除。
- 审批和安全策略贴合生产运维动作。
- 工具证据和会话内工具轨迹。
- 知识库、RAG、AI 记忆、知识金库。
- 可观测业务画像、多系统排查、画像发现、profile packs。
- 实时画板。
- 中文优先的 AIOps 工作台。

## 26. 哪些 OpsCore 明显不如 OpenOcta

- 单包部署和桌面/服务形态。
- 统一 WebSocket Gateway 和事件协议。
- IM 通道运行时，尤其企业微信智能机器人/飞书/钉钉入站。
- 数字员工/角色专属 Skills/MCP。
- LLM Trace/运行回放中心。
- Logs/Debug/Usage 页面。
- Config schema 与 Env vars 页面。
- MCP 一等配置。
- Cron 的 `at/every/cron/timezone/delivery` 抽象。
- 会话 compact/分享/批量管理的一些小体验。
- 文档体系化程度。

## 27. 针对当前巡检问题的优化落点

你最近遇到的问题包括：立即巡检失败、弹窗卡住、进度不可见、企业微信没发、AI 巡检超时、报告没记录、暂停后列表乱跳、多任务交互差、报告需要下拉和删除。

结合 OpenOcta，对 OpsCore 应做：

1. 巡检运行事件化：每个 run 写入事件流，不只最后写报告。
2. 前端从“等待接口返回”改成“提交后看 run 状态”：立即巡检不阻塞弹窗。
3. 运行记录下拉：每个计划卡片折叠展示最近 N 条报告。
4. 报告删除：已有基础，继续补确认、loading、打开报告时同步关闭。
5. 通知状态入库：notification_result 写入 run，并在 UI 展示成功/失败/跳过。
6. 超时显示明确：按 Oracle/数据库/SSH 显示预计上限，允许计划级覆盖。
7. 多任务队列视图：运行中、排队、失败、完成分组。
8. 取消语义明确：取消当前 run，不影响其他计划；UI 不自动跳到其它任务。
9. 报告存储升级：`inspection_runs.json` 短期可用，长期建议 SQLite/JSONL。
10. AI Trace 关联巡检 run：用户可看到卡在哪个模型/工具/资产/通知。

## 28. 推荐实施路线

第一阶段：补巡检体验和可靠性。

- 巡检运行事件表/JSONL。
- 报告下拉、删除、通知状态。
- 立即巡检异步化，前端不阻塞。
- 运行中进度、取消、超时说明。

第二阶段：AI Trace 中心。

- 会话 Trace。
- 巡检 Trace。
- 工具/审批/通知/报告写入统一时间线。
- 支持按 run_id/session_id/asset_id 查询。

第三阶段：通道中心。

- 企业微信 webhook 稳定化。
- 通知发送记录。
- 企业微信智能机器人入站作为高级模式。
- 钉钉/邮件统一为 Channel。

第四阶段：运维专家包。

- 专家角色：Prompt、Skills、工具白名单、MCP、默认模型、默认巡检模板。
- 巡检计划可选择专家角色。
- 会话可切换专家角色。

第五阶段：配置和部署工程化。

- 配置 Schema/导入导出/差异预览。
- 状态目录整理。
- Docker Compose/Windows 服务/一键启动包。

## 29. 不建议采纳的部分

- 不建议把 OpsCore 改成通用 Agent 控制台。
- 不建议直接复制 OpenOcta GPLv3 源码。
- 不建议优先做社区、教程、关于我们、TTS、voice wake。
- 不建议让 MCP 取代现有协议原生工具。
- 不建议把资产中心弱化成 Agent workspace。

## 30. 最终判断

OpenOcta 是一个很好的“通用 Agent 工程底座参考”，但不是 AIOps 产品参考的全部答案。OpsCore 已经在真实运维核心路径上更深，尤其资产、协议、巡检、审批、知识、可观测这些方向明显更符合你的目标。

下一步应该把 OpenOcta 的控制面工程能力吸收到 OpsCore：

- 用它的 Gateway/Trace/Channel/Cron/数字员工思路补 OpsCore 的工程短板。
- 用 OpsCore 的资产/协议/巡检/可观测语义重塑这些能力。
- 最终形成“资产驱动的 AIOps Agent 平台”，而不是“泛企业聊天 Agent”。
