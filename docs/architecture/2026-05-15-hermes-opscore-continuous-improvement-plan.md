# OpsCore 对标 Hermes 的持续优化循环计划

日期：2026-05-15

## 1. 目标

本计划用于把 OpsCore 持续改造成更成熟的 AIOps 平台。后续每一轮开发都按同一个闭环推进：

```text
选择一个小任务
-> 分析现状和影响范围
-> 实施最小可验证改动
-> 自动化验证和必要的页面验证
-> 回比 Hermes/OpsCore 差距表
-> 更新计划状态和下一轮任务
```

目标不是把 OpsCore 复制成 Hermes，而是吸收 Hermes 在通用 Agent 运行时、记忆、会话搜索、上下文压缩、技能学习和多 Agent 协同上的成熟做法，同时保留 OpsCore 自己的 AIOps 主线：资产、协议、工具证据、审批、安全策略、巡检、可观测、知识库和运维报告。

## 2. 固定工作流

每轮开发必须执行以下步骤。

### 2.1 轮次开始

- 明确本轮只解决一个主问题，避免一次改动跨越太多模块。
- 查看 `git status --short`，识别已有脏改。
- 不碰 `.research/hermes-agent/`，除非用户明确要求 Hermes 源码工作。
- 如果涉及函数、类或方法改动，按 `AGENTS.md` 要求先做 GitNexus 影响分析。
- 若任务涉及前端交互，先确认当前页面和数据流，不只看源码。

### 2.2 实施原则

- 优先纵向切片：后端模型、接口、前端入口、验证一起形成一个能运行的小闭环。
- 不新增大而空的框架。
- 不恢复用户已经否定的统一扩展协议路线。
- 告警模块由其他人开发，除非用户明确要求，不主动改告警。
- 资产中心方向可以继续做，但以核心资产目录为主，不走扩展协议。
- 运维写入、外发、破坏性操作必须继续走受控策略和审批链。

### 2.3 轮次验收

每轮结束前至少完成：

- 代码层验证：相关单测、构建或 targeted check。
- 工作树检查：确认没有混入无关文件。
- 若涉及提交：运行 `python scripts/preflight.py --check-git` 和 `python scripts/worktree_audit.py --check-staged`。
- 若涉及前端：通过浏览器或截图验证关键路径。
- 更新本计划中的状态表，写清楚本轮完成项、遗留项和下一轮建议。

### 2.4 回比规则

每轮完成后都要回答这四个问题：

1. 本轮是否缩小了 OpsCore 和 Hermes 在 Agent 运行时上的差距？
2. 是否保持了 OpsCore 的 AIOps 主线，没有变成通用聊天助手？
3. 是否增加了可验证证据、审计、策略或学习闭环？
4. 是否引入了新的复杂度，如果有，是否有明确收益和测试覆盖？

## 3. 对标维度和当前差距

| 维度 | Hermes 强项 | OpsCore 当前状态 | 优先级 | 方向 |
| --- | --- | --- | --- | --- |
| 记忆边界 | `USER.md` / `MEMORY.md` 分离，启动快照冻结 | 已有会话记忆、资产画像、反馈记忆，但分类和提升规则还不够清晰 | P0 | 建立记忆候选、提升、审核、冲突和引用链 |
| 记忆安全 | 注入扫描、不可见字符拦截、memory-context 流式清理 | 已有脱敏和作用域隔离，缺流式泄漏清理 | P0 | 增加记忆/知识/技能上下文安全扫描和输出 scrubber |
| 会话搜索 | SQLite FTS5 + CJK trigram 搜索历史消息和工具调用 | 有消息存储和 trace，但不是一等 session_search 能力 | P0 | 增加会话搜索 API、工具和前端入口 |
| 上下文引擎 | 独立 context engine 生命周期和压缩策略 | prompt 拼装、记忆检索、截断逻辑分散 | P1 | 新增 `ContextEngine`，分离检索、压缩和证据保留 |
| 技能学习 | 复杂任务后沉淀 skill，发现过时 skill 立即修 | OpsCore 有技能演进能力，但缺自动候选生成和质量闭环 | P1 | 从成功工具链、反馈和重复故障生成 skill/runbook 候选 |
| 多 Agent 协作 | Kanban、心跳、阻塞、完成、交接 | 有会话和执行轨迹，缺运维任务板 | P2 | 做 AIOps Run Board，不做普通项目管理看板 |
| 工具注册 | registry + toolsets + 动态可用性 | 已有工具策略元数据，执行层还在逐步收口 | P1 | 让策略、超时、重试、并发、安全门禁真正进入执行层 |
| 生命周期 Hook | gateway/session/agent/tool/API/subagent hooks，失败不阻塞主链路 | 有 Webhook、审批、trace、通知记录，但缺统一内部 hook 面 | P1 | 建立 OpsCore Run Hook 事件面，所有跨模块动作先发事件再订阅 |
| Agent Loop 防失控 | 迭代预算、并行分类、中断转向、任务心跳、runaway 防护 | 有 max_steps、取消、并发安全、超时重试，但 loop 状态还不够产品化 | P0-P1 | 明确 Chat/Headless/Cron/Multi-agent loop 的预算、心跳、取消、重复动作检测 |
| Prompt 架构 | PromptBuilder、记忆指南、工具使用强制、上下文注入扫描、Skill 索引缓存 | 已有 prompt pack、权限提示、证据契约和辅助审查，但缺全局 prompt 生命周期治理 | P0 | 模块化、版本化、证据优先、安全学习、辅助模型审核 |
| 网关通道 | 多平台 gateway 和 channel | OpsCore 通知偏运维，通用通道中心较弱 | P3 | 只围绕审批、通知、巡检、报告强化企业微信/飞书/邮件等 |
| UI 治理 | TUI/Web/Gateway 多入口 | OpsCore 页面多，但复杂列表、报告、记忆治理仍需产品化 | P2 | 学习中心、历史证据、运行时间线、上下文状态可视化 |
| 工程体系 | 大量 runtime/memory/context/gateway 测试 | OpsCore 测试已有基础，但关键运行时仍需补齐 | P0-P3 | 每个闭环必须带 targeted tests |

## 4. 阶段计划

### Phase 0：记忆和学习闭环打底

目标：让 OpsCore 的 AI 记忆从“能保存”升级为“能治理、能学习、能验证”。

任务：

- [ ] 定义记忆分类和提升策略：用户偏好、平台规则、会话状态、成功经验、错误反馈、资产画像、runbook 候选、skill 候选、审计归档。
- [ ] 增加记忆候选机制：用户点赞、成功工具链、重复故障修复、人工纠错后生成候选。
- [ ] 增加候选审核入口：确认后才进入长期记忆、Runbook 或 Skill。
- [ ] 增加记忆冲突提示：同一资产、同一问题出现相反结论时不静默覆盖。
- [ ] 增加记忆引用可回查：AI 回答能展示引用了哪条记忆、何时生成、来自哪个会话。
- [ ] 增加记忆安全扫描：拦截 prompt injection、不可见字符、疑似密钥和外部指令污染。
- [ ] 增加 `<opscore-memory-context>` 输出 scrubber，避免内部上下文泄漏到用户可见消息。

验收：

- [ ] 会话反馈能产生候选记忆。
- [ ] 候选记忆未经确认不会进入长期可召回记忆。
- [ ] AI 回复下方能看到记忆引用来源。
- [ ] 安全扫描能阻止包含明显注入指令的记忆写入。
- [ ] targeted tests 通过。

### Phase 1：Session Search 和 Context Engine

目标：让 Agent 能主动查历史处理经验，并在长会话中稳定保留关键证据。

任务：

- [ ] 为会话消息、工具调用、审批、执行 trace 建立 FTS5/CJK 检索。
- [ ] 增加 `session_search` 后端能力和模型可调用工具。
- [ ] 前端增加“历史证据/历史处理”入口。
- [ ] 新增 `ContextEngine` 接口，统一管理上下文预算、压缩、证据保留和记忆注入。
- [ ] 区分“长期记忆检索”和“当前会话压缩”，避免两者混用。
- [ ] 在 UI 展示上下文状态：原始消息、压缩摘要、保留证据、丢弃区间。

验收：

- [ ] 能按资产 IP、工具名、错误文本、SQL 片段检索历史会话。
- [ ] 长会话压缩后仍保留关键工具证据和审批记录。
- [ ] 模型不能把历史经验当成当前资产已验证事实。

### Phase 2：技能和 Runbook 学习

目标：把重复成功的运维路径沉淀为可复用能力。

任务：

- [ ] 从成功工具链生成 Runbook 候选。
- [ ] 从重复任务生成 Skill 候选。
- [ ] 记录 skill 使用次数、成功率、最近失败、适用资产类型和版本来源。
- [ ] 增加 skill 过时提示：当工具、资产协议或错误反馈证明 skill 不再可靠时进入待修复。
- [ ] 建立 skill/runbook 的审批、版本、回滚和引用链。

验收：

- [ ] 同类问题第二次出现时能推荐历史 Runbook 或 skill。
- [ ] 过时 skill 不会继续被模型无提示地优先使用。
- [ ] 用户能看到 skill 是从哪次运维过程沉淀来的。

### Phase 3：AIOps Run Board

目标：让复杂运维任务不再只依赖聊天滚动记录。

任务：

- [ ] 建立 Run、Stage、Target、ToolCall、Approval、Evidence、Handoff 的任务模型。
- [ ] 增加任务心跳、阻塞原因、取消、恢复和完成交接。
- [ ] 将巡检、排障、变更、报告生成统一进入运行时间线。
- [ ] 前端增加任务板和运行时间线视图。

验收：

- [ ] 一个多资产排障任务能看见每个资产的状态、证据和阻塞点。
- [ ] 任务中断后能恢复上下文，而不是只能从聊天记录里找。
- [ ] 最终报告能索引到完整执行证据。

### Phase 4：执行层策略闭环

目标：让工具元数据真正参与调度和执行，不只用于展示。

任务：

- [ ] `operation_mode` 控制只读、读写受控、写入工具的执行路径。
- [ ] `approval_policy` 统一进入审批 gate。
- [ ] `destructive` 工具默认强制阻断或强制人工确认。
- [ ] `timeout_policy` 和 `retry_policy` 接入执行调度。
- [ ] `concurrency_safe` 控制多资产并发，只读安全工具可并发，写入/外发工具串行或审批。
- [ ] 前端策略标签区分“只读模式下禁止写入”和“读写模式下写入受控”，避免用户误解。

验收：

- [ ] 读模式下写入工具显示为禁止或需切换模式，不再和读写模式同文案。
- [ ] 读写模式下写入工具进入受控审批，不显示成完全自由执行。
- [ ] 并发调度不会自动并发执行危险写入工具。

### Phase 4.5：Hook、Loop、Toolset 和 Prompt 架构闭环

目标：把 Hermes 值得借鉴的“可组合工具、生命周期 hook、受控 agent loop、提示词工程体系”转成 OpsCore 自己的 AIOps 运行时底座。这里不复制 Hermes，不引入新的耦合层，而是补 OpsCore 缺的中立合同。

#### 4.5.1 OpsCore Run Hook

后端先定义内部事件面，功能模块只能订阅事件，不能互相硬 import：

- `run:start`：AIOps Run、巡检、排障、报告或后台任务启动。
- `agent:step`：每次模型回合、工具回合或后台子任务回合。
- `tool:before` / `tool:after`：工具执行前后，写入策略、审批、证据、耗时、错误。
- `approval:requested` / `approval:resolved`：审批申请和审批结果。
- `context:compact`：上下文压缩、证据保留和丢弃区间。
- `memory:candidate` / `learning:candidate`：候选记忆、Runbook 候选、Skill 候选产生。
- `notification:sent`：企业微信、飞书、邮件等通知发送结果。
- `run:blocked` / `run:cancelled` / `run:end`：阻塞、取消、完成和最终交接。

原则：

- Hook 失败只能记录审计和告警，不阻断主链路，除非该 hook 明确是 policy gate。
- Hook payload 只能携带 ID、摘要、证据引用和脱敏字段，不携带明文凭证。
- 告警模块由其他人开发，OpsCore 这里只定义可接入事件合同，不主动改告警逻辑。

#### 4.5.2 Agent Loop 和后台 Loop

OpsCore 至少要把四类 loop 显式化：

- Chat loop：用户会话里的模型-工具循环。
- Headless loop：巡检、定时任务、后台协同任务。
- Multi-agent loop：全局模式、组模式、单会话模式的多 Agent 分发与回收。
- Cron/Inspection loop：计划任务、批量资产任务、周期报告。

每个 loop 必须具备：

- `max_turns` / `max_steps`：最大回合数。
- `timeout_policy`：单工具、单目标、整轮任务超时。
- `retry_policy`：只对允许重试的错误重试，写入/外发/破坏性动作默认不重试。
- `cancel_token`：用户取消、暂停、恢复要进入统一状态，不在 UI 里乱跳。
- `heartbeat`：长任务持续写入进度，前端能看到正在做什么。
- `spin_guard`：检测重复调用同一工具、同一参数、同一失败结果，防止无限循环。
- `finalize`：无论成功、失败、超时、取消，都生成结构化结论和证据索引。

#### 4.5.3 Hermes Toolset 全量对照

Hermes 当前源码里的核心 toolset 能力可分三层吸收：

必须进入 OpsCore 核心目录：

- Web / Browser：`web_search`、`web_extract`、浏览器导航、点击、截图、控制台、图片读取。
- File：只读文件、搜索文件、受控写入、patch。
- Terminal / Process：主机命令、进程管理，必须走资产权限和审批。
- Memory / Session Search / Todo：记忆、历史会话检索、任务步骤。
- Skills：Skill 列表、查看、管理、候选生成、审核、发布草稿。
- Delegation / Multi-agent：子 Agent、组模式、全局模式、任务交接。
- Cronjob：计划任务、暂停、恢复、手动触发。
- Code execution：受控脚本执行，只允许在明确环境和权限下运行。

按通道或场景接入：

- Messaging：企业微信、飞书、钉钉、邮件、Slack/Telegram/Discord 等只作为通道中心能力。
- Vision / Image / TTS / Voice：用于报告、截图分析、语音/图片场景，默认不是运维核心入口。
- MCP：作为外部工具桥接能力，但必须继承 OpsCore 工具策略和证据记录。

暂不作为核心优先级：

- HomeAssistant、Spotify、游戏/媒体类、平台私有社交工具等非 AIOps 主线能力。
- CUA 桌面控制只作为高级受控能力，不能成为默认运维路径。

验收：

- [ ] 生成 Hermes toolset vs OpsCore tool registry 对照表，标记 `available`、`controlled`、`not_wired`、`not_applicable`。
- [ ] 工具中心按“运维核心 / 通道 / 学习 / 受控危险 / 暂未接入”分组展示。
- [ ] 新增工具必须带 `operation_mode`、`approval_policy`、`evidence_family`、`timeout_policy`、`retry_policy`、`concurrency_safe`。

#### 4.5.4 AIOps Prompt 让运维越来越聪明且安全

Prompt 不再当成一段大文本，而是按职责组装：

- Base identity：OpsCore 是 AIOps 平台，不是通用聊天玩具。
- AIOps role：面向资产、系统、数据库、网络、存储、虚拟化、日志平台和业务链路排障。
- Permission context：全局/组/会话权限上限、只读/读写受控、审批策略。
- Tool context：当前可用工具、不可用工具、受控工具、证据类型和并发限制。
- Asset/session context：资产画像、协议、凭证可用性、历史风险、当前会话目标。
- Evidence contract：当前事实必须来自实时工具证据；历史记忆只能作为线索。
- Memory/RAG context：记忆、知识库和历史经验必须带来源、时间和可信度。
- Learning policy：只有经过辅助模型审核和人工确认的经验才能晋升为 Runbook/Skill。
- Safety policy：禁止泄露凭证，禁止无审批写入，禁止把模拟结果说成真实执行。
- Output contract：排障结论必须区分“已验证事实 / 推断 / 待验证 / 建议动作”。

关键提示词规则：

- 先只读验证，再提出写入或变更动作。
- 写操作、外发通知、删除、重启、配置变更、批量任务必须经过统一 gate。
- 如果没有工具证据，回答必须标注“不确定”或“待验证”。
- 辅助模型负责自动审核候选记忆、Runbook、Skill、报告摘要和高风险动作说明。
- 记忆不能保存密码、Token、私钥、Cookie、完整连接串或一次性临时状态。
- 成功经验只能沉淀为候选，不能直接进入长期检索上下文或自动执行。

验收：

- [ ] Prompt pack 有版本号和变更记录。
- [ ] 每次 Run 记录实际注入的 prompt 模块清单，不记录密钥和完整私有上下文。
- [ ] 辅助模型能给候选学习输出 `accept / needs_human_review / reject`、风险、缺失项和建议类型。
- [ ] 前端只显示简洁动作：查看建议、生成草稿、确认、忽略、查看证据。

### Phase 5：通道、报告和知识联动

目标：把通知、HTML 报告、知识库、记忆和执行证据连成闭环。

任务：

- [ ] 企业微信/飞书/邮件通知记录发送结果、失败原因和重试。
- [ ] HTML 报告支持本地离线查看，主页索引到每份报告。
- [ ] 报告能引用工具证据、记忆、RAG 资料和 Runbook。
- [ ] 报告入库后可被 RAG 检索，但不直接变成正向记忆。
- [ ] 通知内容区分摘要、失败原因、证据链接和本地报告路径。

验收：

- [ ] 本地打开 HTML 报告无需后端服务也能查看主体内容。
- [ ] 报告中心能管理几十到上百份报告，支持搜索、筛选、删除、归档预览。
- [ ] 通知失败不会造成报告丢失。

## 5. 每轮复盘模板

每轮完成后，在本文件追加一条记录：

```markdown
### YYYY-MM-DD Round N：任务名

- 完成：
- 验证：
- Hermes 差距变化：
- OpsCore 主线影响：
- 遗留风险：
- 下一轮建议：
```

## 6. 当前建议的下一轮

下一轮从 Phase 0 开始，优先实现“记忆候选和提升策略”的最小闭环：

```text
用户反馈/成功工具链
-> 生成候选记忆
-> 前端学习中心展示
-> 人工确认
-> 写入长期记忆
-> 会话回复引用并可回查
```

这个切片收益最大，并且不会干扰当前告警模块、资产中心和巡检已有逻辑。

## 7. 执行记录

### 2026-05-15 Round 1：反馈记忆候选化

- 完成：用户点赞 AI 回答后不再直接进入可检索长期记忆，而是写入 `review_status=pending`、`retrieval_enabled=false` 的候选成功经验；点踩仍作为纠错/避错记忆保留；人工复核会把同一记忆文件中的待确认候选切为 confirmed 并允许检索。
- 验证：`python -m pytest tests/test_memory_policy.py tests/test_file_memory_store.py tests/test_session_message_store.py tests/test_session_history.py` 通过，52 passed；`npm run build` 通过。
- Hermes 差距变化：向 Hermes 的“记忆先治理、再进入上下文”靠近，避免点赞内容未经确认就污染后续模型上下文。
- OpsCore 主线影响：保留 AIOps 的当前会话隔离和实时证据优先原则，反馈记忆仍只在当前 session 范围内生效。
- 遗留风险：候选确认目前复用记忆复核入口，还是按文件级确认；后续需要更细的单条候选审核 UI。
- 下一轮建议：补“学习中心/候选列表”的专用 API 和前端卡片，把候选记忆、Runbook 候选、Skill 候选统一展示。

### 2026-05-15 Round 2：学习候选入口

- 完成：新增 `/knowledge/memory/candidates`，从文件型记忆中列出 `review_status=pending` 的候选条目；知识库 AI 记忆页新增“学习候选”步骤，集中展示候选记忆、待确认冲突、过期复核和质量建议；候选可直接确认沉淀，确认后才允许进入检索上下文。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，68 passed；`npm run build` 通过；临时端口 `8010` 页面烟测确认“学习候选”入口和候选空状态正常渲染。
- Hermes 差距变化：把 Hermes 的“记忆候选先审核、再注入上下文”从后端策略推进到可见治理入口。
- OpsCore 主线影响：入口仍位于知识库 / AI 记忆，不影响资产中心、告警、巡检和工具执行；候选仅当前会话文件记忆范围内治理。
- 遗留风险：候选确认仍按记忆文件执行，文件内多个候选会一起被确认；后续需要 entry 级候选 ID 和单条确认/拒绝。
- 下一轮建议：继续补单条候选状态模型，增加“拒绝候选/转 Runbook 候选/转 Skill 候选”的动作。

### 2026-05-15 Round 3：单条候选确认/拒绝

- 完成：为每条待确认记忆候选生成稳定 `candidate_id`；新增单条候选处理能力，支持 `confirm` 和 `reject`，确认只提升目标候选为可检索，拒绝只保留审计且不进入模型上下文；前端学习候选卡片新增候选 ID 和“拒绝候选”动作。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，70 passed；`npm run build` 通过；临时端口 `8010` 页面烟测确认学习候选入口、候选 ID/空状态和拒绝动作区域可渲染。
- Hermes 差距变化：进一步接近 Hermes 的细粒度记忆治理，不再以整个记忆文件作为最小审核单位。
- OpsCore 主线影响：仍只作用于 AI 记忆治理，不影响资产、告警、巡检和工具执行链路；拒绝候选默认作为审计记录保留。
- 遗留风险：候选仍存放在 Markdown 文件中，单条改写依赖 Markdown entry 结构；后续若候选量变大，应增加 SQLite 索引表或候选 manifest。
- 下一轮建议：增加“转 Runbook 候选 / 转 Skill 候选”的动作，以及候选来源的工具证据引用。

### 2026-05-15 Round 4：候选转 Runbook/Skill

- 完成：候选记忆处理动作扩展为 `confirm`、`reject`、`to_runbook`、`to_skill`；转 Runbook/Skill 只更新候选状态和类型，保持 `retrieval_enabled=false`，不会直接进入模型检索或生成自动化文件；前端学习候选卡片新增“转 Runbook”和“转 Skill”动作。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，72 passed；`npm run build` 通过。
- Hermes 差距变化：补齐从经验候选到可复用运维资产的中间状态，避免经验直接污染记忆，也避免未经实现测试就变成 Skill。
- OpsCore 主线影响：仍限定在 AI 记忆治理入口，不触碰资产中心、告警和巡检链路。
- 遗留风险：Runbook/Skill 候选目前仍写在 Markdown 记忆文件中，尚未进入独立的 Runbook/Skill 生命周期、审批、测试和版本管理。
- 下一轮建议：给候选补工具证据引用和来源链路，再决定是否建立 Runbook/Skill 候选池。

### 2026-05-15 Round 5：候选来源证据链

- 完成：点赞生成的候选记忆写入 `source_refs` 和 `evidence_refs`；候选列表读取时兼容历史数据，自动补来源会话、反馈消息和记忆文件路径；学习候选卡片新增“来源链”和“工具证据”区域。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，72 passed；`npm run build` 通过。
- Hermes 差距变化：开始把“为什么这条经验可以学习”显式化，向 Hermes 式可追溯学习靠近。
- OpsCore 主线影响：仅扩展 AI 记忆候选元数据和展示，不改变工具执行、资产、告警、巡检。
- 遗留风险：目前只绑定反馈目标消息和已有 `exec_trace` 中的证据 ID，尚未提供点击跳转到具体工具结果详情。
- 下一轮建议：增加候选卡片的“定位会话消息/查看工具证据”跳转，并把 Runbook/Skill 候选池独立出来。

### 2026-05-15 Round 6：候选定位会话消息

- 完成：学习候选卡片新增“定位消息”，可按候选来源会话切回会话页并聚焦反馈目标消息；会话消息列表的滚动定位同时识别前端消息 ID、后端 `memoryId/_memory_id` 和 `mem-{id}` 形式，避免历史消息因 ID 形态不同无法定位。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，79 passed；`npm run build` 通过。
- Hermes 差距变化：候选学习不再只看到摘要，开始能回到原始会话上下文核验来源。
- OpsCore 主线影响：只复用现有知识库和会话页事件机制，不新增运行时后端链路。
- 遗留风险：工具证据仍只展示 ID/工具/状态，尚未打开具体执行轨迹详情。
- 下一轮建议：为 `evidence_refs` 增加“查看证据详情”面板，优先复用会话消息上的 `execTrace`。

### 2026-05-15 Round 7：候选工具证据详情

- 完成：学习候选的工具证据可点击打开详情弹窗；前端优先从已加载会话消息匹配 `execTrace`，未加载时按来源会话拉取历史并匹配 `evidenceId`、`toolCallId` 或工具名；匹配成功后复用现有 `ToolTraceList` 展示工具、策略、执行内容、结果和 evidence metadata。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py tests/test_session_history.py` 通过，80 passed；`npm run build` 通过。
- Hermes 差距变化：候选学习从“可追溯到消息”推进到“可追溯到真实工具证据”，减少无证据经验进入 Runbook/Skill 候选的风险。
- OpsCore 主线影响：仍只在知识库前端复用会话历史和执行轨迹，不新增后端接口，不触碰资产、巡检、告警执行。
- 遗留风险：如果历史会话没有加载到对应 `execTrace`，只能展示证据引用和未匹配提示；后续可增加按 evidence_id 直接查询的后端接口。
- 下一轮建议：把 Runbook/Skill 候选从 Markdown 记忆里抽成独立候选池，带来源消息和证据引用。

### 2026-05-15 Round 8：Runbook/Skill 候选分流展示

- 完成：`/knowledge/memory/candidates` 支持按 `review_status` 查询 `pending`、`runbook_candidate`、`skill_candidate`；学习候选页把待确认候选、Runbook 候选、Skill 候选分成三个区域，转换后的候选不再从界面消失，同时仍保持 `retrieval_enabled=false`，不会进入模型检索上下文。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py` 通过，43 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：补齐经验候选到 Runbook/Skill 的可见中间态，避免“转了以后找不到”，更接近 Hermes 的学习资产生命周期。
- OpsCore 主线影响：只扩展知识库 AI 记忆治理入口和候选查询参数，不触碰资产、巡检、告警执行。
- 遗留风险：Runbook/Skill 候选仍存放在 Markdown 记忆文件中，还不是独立生命周期对象；后续需要真正的候选池、发布审批、测试校验和版本记录。
- 下一轮建议：建立独立 Runbook/Skill 候选池或先增加 evidence_id 后端查询接口，减少前端必须拉整段会话历史才能看证据的依赖。

### 2026-05-15 Round 9：候选证据后端直查

- 完成：新增 `/session/{session_id}/history/evidence`，可按 `evidence_id`、`tool_call_id` 或 `tool` 从会话历史中定位单条 `exec_trace`，返回匹配 trace 和来源消息摘要；学习候选工具证据弹窗优先调用该接口，失败时再回退到原来的整段历史加载。
- 验证：`python -m pytest tests/test_session_history.py tests/test_session_history_service.py tests/test_tool_policy_runtime_frontend.py tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_memory_policy.py tests/test_session_message_store.py` 通过，91 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：证据查看从前端“拉全量再猜”推进到后端按证据索引查找，更适合后续做长期审计、Runbook 发布和 Skill 校验。
- OpsCore 主线影响：新增的是只读会话历史查询接口，不改变工具执行、审批、安全策略、资产、巡检、告警链路。
- 遗留风险：当前仍基于会话消息里的 `exec_trace` 扫描，尚未建立独立 evidence 索引表；历史消息压缩或清理后，旧证据可能只能看到引用 ID。
- 下一轮建议：为 Runbook/Skill 候选建立独立候选池，并在候选对象上保存 `source_session_id`、`feedback_message_id`、`evidence_refs`、状态流和发布记录。

### 2026-05-15 Round 10：Runbook/Skill 独立候选池

- 完成：候选记忆执行 `to_runbook` 或 `to_skill` 时，除更新 Markdown 记忆状态外，还写入 `learning_candidates.jsonl` 独立候选池；新增 `/knowledge/memory/learning-candidates` 查询接口；学习候选页新增“发布候选池”，展示目标类型、状态、来源会话、来源文件、证据数量和下一步动作。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py` 通过，43 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Runbook/Skill 候选不再只藏在 Markdown 记忆条目里，开始具备独立生命周期对象，向 Hermes 的技能学习/演进队列靠近。
- OpsCore 主线影响：候选池只是审计和治理对象，不会自动发布 Skill、不会自动执行 Runbook，也不改变资产、巡检、告警和工具执行链路。
- 遗留风险：候选池目前是 JSONL 文件，还没有状态变更接口、发布审批、版本回滚、重复候选合并和全文索引。
- 下一轮建议：给发布候选池补状态流接口，支持 `draft -> reviewing -> approved/rejected -> published`，并记录每次状态变更的操作者和理由。

### 2026-05-15 Round 11：发布候选状态流

- 完成：发布候选池支持状态更新，状态范围为 `draft`、`reviewing`、`approved`、`rejected`、`published`；新增 `PATCH /knowledge/memory/learning-candidates/{candidate_id}/status`，要求填写操作者和理由；候选对象记录 `status_events` 状态事件；前端发布候选池新增提交评审、批准、拒绝、标记发布按钮，并显示最近状态流。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py` 通过，44 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Runbook/Skill 学习候选开始具备可审计生命周期，不再只是静态列表。
- OpsCore 主线影响：状态流仍是治理层能力，不会自动执行、自动发布或改动现有告警/巡检/资产链路。
- 遗留风险：状态机目前只校验状态集合和理由，尚未严格限制跨状态跳转；`published` 还只是标记发布，不会生成正式 Runbook/Skill 版本。
- 下一轮建议：增加候选详情抽屉和发布前质量清单，至少展示来源消息、工具证据、适用范围、风险边界、测试项和回滚项。

### 2026-05-15 Round 12：发布候选详情和质量清单

- 完成：发布候选对象新增 `quality_checklist`，按 Runbook/Skill 分别列出来源消息、工具证据、适用范围、执行步骤或输入参数、风险边界、测试或验证项、回滚方案；前端发布候选池新增“查看详情”抽屉，集中展示候选摘要、发布前质量清单、来源链、工具证据和状态流。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py tests/test_file_memory_store.py tests/test_knowledge_routes.py` 通过，44 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：学习候选从“能审批状态”推进到“发布前可检查质量门槛”，更接近 Hermes 式技能/经验演进的审计闭环。
- OpsCore 主线影响：仍停留在知识库治理层，不自动生成正式 Runbook/Skill，不改变工具执行、资产、巡检和告警链路。
- 遗留风险：质量清单目前是系统生成的静态 checklist，尚未支持人工勾选、补充说明、发布阻断规则或正式版本生成。
- 下一轮建议：把质量清单升级为可编辑发布表单，并让 `approved/published` 状态校验必要项是否补齐。

### 2026-05-15 Round 13：质量清单可编辑保存

- 完成：新增 `PATCH /knowledge/memory/learning-candidates/{candidate_id}/quality-checklist`，支持保存发布候选的质量清单勾选状态、说明、操作者和变更理由；候选对象记录 `quality_events`；前端详情抽屉把质量清单从静态展示升级为可勾选、可填写说明、可保存的发布表单。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py` 通过，44 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Runbook/Skill 候选已经具备“从经验生成、状态流转、发布前质量门槛、人工补齐记录”的基本闭环。
- OpsCore 主线影响：只写入独立学习候选池，不自动发布、不触发工具执行，不影响资产、巡检、告警。
- 遗留风险：`approved/published` 仍未强制要求质量清单全部通过；质量清单也还没有正式 Runbook/Skill 版本产物。
- 下一轮建议：在状态流转时增加发布门禁，要求进入 `approved` 或 `published` 前关键清单项已通过。

### 2026-05-15 Round 14：发布状态质量门禁

- 完成：发布候选进入 `approved` 或 `published` 前，后端强制要求质量清单全部通过；前端发布候选池同步禁用批准/发布按钮，并提示需先补齐并保存发布前质量清单。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py` 通过，44 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：学习候选生命周期从“有清单”推进到“清单真正参与发布门禁”，更接近可治理的技能演进流程。
- OpsCore 主线影响：门禁只约束学习候选状态流转，不自动执行、不自动发布，不影响资产、巡检、告警。
- 遗留风险：门禁目前要求全部清单项通过，尚未区分必填项和建议项；正式 Runbook/Skill 版本产物仍未生成。
- 下一轮建议：增加正式发布产物草稿，把 `published` 候选转换为 Runbook/Skill 草稿文件或记录，同时保留来源证据链。

### 2026-05-17 Round 15：发布产物草稿模板

- 完成：`published` 学习候选生成的 Markdown 发布草稿升级为 Runbook/Skill 分类型模板；Runbook 草稿包含适用场景、执行前检查、执行步骤、验证退出标准和回滚方案；Skill 草稿包含建议目录结构、输入参数、安全边界、验证计划和回滚方案。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py -q` 通过，41 passed；`pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，13 passed；`python scripts/preflight.py --check-git` 通过，1280 tests。
- Hermes 差距变化：从“候选可发布”推进到“候选能形成可审查的运维资产草稿”，更接近 Hermes 的技能学习和演进产物，但仍不自动安装、不自动执行。
- OpsCore 主线影响：只增强知识库学习候选的草稿内容，不改变资产、巡检、告警或工具执行链路。
- 遗留风险：草稿仍是 Markdown 审核产物，尚未生成正式 Skill 目录、Runbook 版本表、灰度发布记录或回滚版本。
- 下一轮建议：增加发布草稿校验结果，Skill 草稿接入 `validate_skill_candidate` 风格的结构检查，Runbook 草稿接入必备章节检查。

### 2026-05-17 Round 16：Hook/Loop/Tools/Prompt 架构补齐计划

- 完成：把 Hermes 源码和架构文章中值得吸收的 hook、agent loop、toolset、prompt/memory guidance 归纳进本持续计划；同时在 `AGENTS.md` 增加全局架构规则，要求后续跨模块功能通过事件、运行记录、工具策略和学习候选解耦。
- 验证：本轮为文档和架构约束更新，未改业务代码；后续提交前仍需运行 preflight 和 staged audit。
- Hermes 差距变化：差距表从“记忆/技能学习”扩展到“运行时生命周期、loop 防失控、工具全集、提示词治理”，避免后续只在页面上修补。
- OpsCore 主线影响：明确 OpsCore 只吸收对 AIOps 有价值的能力，不复制非运维工具；前端保持简约，复杂治理留在后端。
- 遗留风险：目前是架构计划，还没有实现统一 Run Hook、spin guard、toolset 对照表和 prompt 版本审计。
- 下一轮建议：优先做 Hermes toolset vs OpsCore tool registry 对照表，然后实现最小的 `run_hooks` 事件总线和 loop 心跳/重复动作检测。

### 2026-05-17 Round 17：Hermes/OpsCore 工具全集对照

- 完成：新增 `docs/architecture/2026-05-17-hermes-opscore-toolset-inventory.md`，从 Hermes `toolsets.py` 聚合 79 个唯一工具，从 OpsCore `tool_registry` 读取 62 个当前注册工具，并按 `available`、`controlled`、`not_wired`、`adapted`、`not_applicable` 分类。
- 验证：本轮为只读清单和文档更新，未改业务代码；后续提交前仍需运行 staged audit 和 preflight。
- Hermes 差距变化：把“tools 之前没全”的问题拆成可执行清单，明确 OpsCore 该补的是 `session_search`、`delegate_task`、`cronjob`、`execute_code`、`process`、`patch/write_file/skill_manage` 的平台化接入，而不是复制非运维工具。
- OpsCore 主线影响：保留 OpsCore 在资产协议、数据库、监控日志、网络、存储、虚拟化、K8s、CI/CD、大数据和通知审计上的优势；不把 Spotify、HomeAssistant、RL、Yuanbao 等非 AIOps 工具放入核心。
- 遗留风险：当前只是文档对照，工具中心前端还没有新的分组筛选，`session_search` 和 `delegate_task` 仍未真正接入执行链。
- 下一轮建议：实现最小 `run_hooks` 事件总线，先覆盖 `run:start`、`agent:step`、`tool:before`、`tool:after`、`run:end`，为后续 loop heartbeat 和 spin guard 做底座。

### 2026-05-17 Round 18：Run Hook 事件总线和工具防重复调用

- 完成：新增 `core/run_hooks.py` 作为轻量内部事件总线，支持精确事件、通配事件、同步/异步 handler、异常隔离和 payload 脱敏；工具执行链在执行前后发出 `tool:before` / `tool:after`；新增 `ToolSpinGuard`，同一工具和参数连续失败达到阈值后返回 `spin_guard` 阻断结果，避免模型进入重复失败循环。
- 验证：`python -m pytest tests/test_run_hooks.py tests/test_agent_tool_loop.py tests/test_agent_chat_loop.py -q` 通过，35 passed。
- Hermes 差距变化：开始把 Hermes 的 lifecycle hook 和 runaway loop 防护落到 OpsCore 运行时，而不是只停留在文档计划。
- OpsCore 主线影响：事件总线不改变现有工具执行结果，只提供审计、学习、可观测和后续 Run Trace 的接入点；防重复调用只拦截连续失败的同工具同参数。
- 遗留风险：当前只覆盖工具前后事件和 chat loop 的重复失败 guard；`run:start`、`agent:step`、`run:end`、headless/cron heartbeat 还需继续接入。
- 下一轮建议：把 `run:start`、`agent:step`、`run:end` 接入 chat/headless loop，并把 hook 事件写入 AIOps Run Trace 或 session trace，前端再显示简单进度。

### 2026-05-17 Round 19：Chat Run 生命周期事件

- 完成：`run_chat_agent_loop` 在单模型和主副模型路径统一发出 `run:start`、`agent:step`、`run:end`，payload 只携带会话、模型、编排模式、步数和受限上下文；hook 异常只记录 warning，不影响会话流式输出。
- 验证：`python -m pytest tests/test_run_hooks.py tests/test_agent_tool_loop.py tests/test_agent_chat_loop.py -q` 通过，35 passed。
- Hermes 差距变化：OpsCore 运行时已经具备最小生命周期 hook，后续可以像 Hermes 一样围绕 run/step/tool 做 trace、审计、记忆学习和防失控治理。
- OpsCore 主线影响：本轮不改变前端交互、不改变工具结果、不新增复杂配置；只是给执行层增加可订阅事件。
- 遗留风险：hook 事件还没有持久化到 AIOps Run Trace；headless/cron/巡检等非 chat 执行路径还未统一接入；前端还看不到 run heartbeat。
- 下一轮建议：先实现 hook 事件到 session trace / run trace 的轻量写入，再考虑 headless/cron heartbeat，避免直接做复杂前端。

### 2026-05-17 Round 20：Headless Run 生命周期事件

- 完成：`run_headless_agent_loop` 接入同一套 run hook，后台协同任务、心跳和巡检等无头执行路径会发出 `run:start`、`agent:step`、`run:end`；事件 payload 只包含会话、模型、Agent 画像、目标 host、步数和受限上下文。
- 验证：`python -m pytest tests/test_agent_headless_loop.py tests/test_agent_chat_loop.py tests/test_run_hooks.py -q` 通过，33 passed。
- Hermes 差距变化：OpsCore 的 chat 与 headless 两条核心执行循环已经都有生命周期事件，具备后续统一 trace、heartbeat 和 loop 审计的入口。
- OpsCore 主线影响：不改变 headless 返回报告、不改变工具执行和审批阻断逻辑；只是增加可选 hook emitter 和默认内部事件。
- 遗留风险：headless 工具级 `tool:before` / `tool:after` 还没有与 chat 工具链完全统一；hook 事件仍未持久化。
- 下一轮建议：新增一个轻量 hook 订阅器，把 run/step/tool 事件写入 session trace 或独立 run trace 文件，供前端后续读取。

### 2026-05-17 Round 21：Run Trace 轻量持久化

- 完成：新增 `core/run_trace_store.py`，默认订阅 `run:*`、`agent:step`、`tool:*` 等 hook 事件并写入隐藏系统审计消息；新增 `GET /session/{session_id}/history/run-trace` 查询会话运行事件；普通会话历史仍不会显示这些审计消息。
- 验证：`python -m pytest tests/test_run_hooks.py tests/test_run_trace_store.py tests/test_session_history.py tests/test_session_history_service.py tests/test_session_history_routes.py tests/test_api_mappers.py tests/test_agent_chat_loop.py tests/test_agent_headless_loop.py -q` 通过，96 passed。
- Hermes 差距变化：OpsCore 不再只有瞬时 hook，已经具备可追溯的 Run Trace 底座，后续可以接入前端进度、学习候选、审批审计和问题复盘。
- OpsCore 主线影响：持久化落在现有 session message store 内，不引入新数据库表和复杂配置；payload 写入前经过脱敏，且 `visible_to_user=false`。
- 遗留风险：当前 run trace 仍是隐藏消息过滤查询，还没有聚合 run_id、耗时统计、前端进度视图和 retention 压缩策略。
- 下一轮建议：给 run trace 增加 run_id 聚合和状态摘要，再做一个简约前端抽屉显示最近运行步骤。

### 2026-05-17 Round 22：右侧链路面板显示 Run Trace

- 完成：前端 `sessionHistory` API 增加 `getSessionRunTrace`；右侧「链路」面板顶部显示 AIOps Run Trace 最近事件，展示 run、step、tool 生命周期摘要、时间和状态，不新增复杂配置或独立页面。
- 验证：`cd frontend && npm run build` 通过；Playwright 打开 `http://127.0.0.1:4173/` 无页面错误，应用正常渲染。
- Hermes 差距变化：Run Trace 从后端审计数据推进到用户可见的简约运行进度视图，接近 Hermes 的运行日志/Trace 可观察体验。
- OpsCore 主线影响：只读展示现有隐藏审计消息，不改变会话消息、工具调用、审批、巡检或告警逻辑。
- 遗留风险：当前只显示最近事件列表，还没有按 run_id 折叠、耗时统计、失败原因聚合和点击定位工具证据。
- 下一轮建议：给 run trace 事件补 run_id 聚合，并在前端按一次运行折叠显示开始、步骤、工具和结束状态。

### 2026-05-17 Round 23：Run Trace 单次运行下钻

- 完成：Run Trace 后端查询支持按 `run_id` 过滤，服务层和前端 API 保持兼容；右侧链路面板新增“全部运行 / 单次运行”选择，默认保持简约总览，选择某个 `run_id` 后只拉取这一轮的完整事件并可一键恢复全部。
- 验证：`python -m pytest tests/test_session_history.py tests/test_session_history_service.py tests/test_session_history_routes.py -q` 通过，32 passed；`cd frontend && npm run build` 通过；Playwright 打开 `http://127.0.0.1:4173/` 应用正常渲染，当前 500 来自本地预览代理访问未运行的 `/api/v1/sessions/active` 后端接口。
- Hermes 差距变化：Run Trace 从“可见最近事件”推进到“可按一次运行下钻”，更接近 Hermes 运行日志中按 run/session 追踪单条任务的体验。
- OpsCore 主线影响：仍是只读审计和进度查看，不改变工具执行、审批、资产、巡检、通知或告警链路。
- 遗留风险：单次运行下钻仍在右侧链路面板内，没有独立 Run 详情页；事件还不能直接跳转到具体工具证据、审批记录或学习候选。
- 下一轮建议：给每个 Run Trace 事件补 `evidence_ref` / `approval_ref` 的前端定位入口，或先做后端 `Run Trace -> Learning Candidate` 的只读候选提取预览。

### 2026-05-17 Round 24：Run Trace 证据和审批引用

- 完成：工具执行结束 hook payload 增加 `evidence_id`，保留已有 `approval_ref`；右侧 Run Trace 事件卡片显示“证据”和“审批”引用，后续报告、审计和学习候选可以直接沿这些 ID 回查。
- 验证：`python -m pytest tests/test_agent_tool_loop.py tests/test_run_trace_store.py tests/test_tool_policy_runtime_frontend.py -q` 通过，27 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Run Trace 不再只是时间线文本，开始携带可回查的证据锚点，更接近 Hermes 的 trace/log 可追溯体验，同时保留 OpsCore 的运维证据链。
- OpsCore 主线影响：只增加审计引用字段和只读展示，不改变工具执行结果、审批决策、资产、巡检、通知或告警逻辑。
- 遗留风险：当前只是显示 ID，尚未提供点击打开工具证据详情、审批详情或学习候选预览。
- 下一轮建议：复用知识库候选的 evidence dialog，给 Run Trace 的证据 ID 增加“查看证据详情”入口。

### 2026-05-17 Round 25：Run Trace 证据详情入口

- 完成：右侧 Run Trace 里的证据 ID 从静态标签升级为可点击入口；点击后复用现有 `/session/{session_id}/history/evidence` 查询和 `ToolTraceList` 展示完整工具执行轨迹、策略、实际动作、结果和证据元数据。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py tests/test_session_history.py tests/test_session_history_service.py tests/test_session_history_routes.py -q` 通过，47 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Run Trace 已经能从时间线跳到工具证据详情，形成 run -> tool -> evidence 的追踪链，进一步接近 Hermes 的 trace 可回放能力。
- OpsCore 主线影响：只读查询会话历史中的既有工具轨迹，不改变执行、审批、资产、巡检、通知或告警链路。
- 遗留风险：审批引用仍只是显示 ID，尚未点击打开审批详情；证据详情只在当前会话历史可查时可用，历史清理后还需要独立 evidence 索引支撑。
- 下一轮建议：给审批引用增加审批详情入口，或先抽象一个通用 EvidenceRef 组件，避免知识库、Run Trace、报告页面重复实现证据打开逻辑。

### 2026-05-17 Round 26：Run Trace 审批详情入口

- 完成：前端审批 API 增加只读 `getApproval`；右侧 Run Trace 的审批引用从静态 ID 升级为可点击入口，弹窗展示审批状态、工具、审批来源、会话、资产、申请时间、处理人、处理结果和参数。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py tests/test_interaction_approval_skill_routes.py -q` 通过，24 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：Run Trace 现在可从 run -> tool -> evidence / approval 两条链路下钻，审计闭环更接近 Hermes 的可追踪运行记录。
- OpsCore 主线影响：审批详情入口只读，不提供批准、拒绝或执行动作，不改变审批决策、工具执行、资产、巡检、通知或告警链路。
- 遗留风险：证据和审批详情弹窗仍在 Run Trace 面板内部各自实现，和知识库、报告页还没有共用组件。
- 下一轮建议：抽出通用 `EvidenceRefButton` / `ApprovalRefButton` 或 Run Trace detail components，减少知识库、报告、Run Trace 的重复实现。

### 2026-05-17 Round 27：Run Trace 学习候选提交去重

- 完成：Run Trace 学习候选提交按 `session_id + run_id` 查重；重复提交时返回已有 Runbook 学习候选，不再重复写入候选池；学习候选记录保留 `run_id`，便于后续审计和前端定位来源运行。
- 验证：`python -m pytest tests/test_session_history_service.py tests/test_file_memory_store.py -q` 通过，38 passed；`python scripts/preflight.py --check-git` 通过，1298 tests；`python scripts/worktree_audit.py --check-staged` 通过；GitNexus staged 变更检测已复核。
- Hermes 差距变化：学习候选不再因为重复点击或重新打开预览而产生多份相同草稿，候选池生命周期更接近可治理队列。
- OpsCore 主线影响：只影响学习候选提交路径，不改变工具执行、审批、资产、巡检、通知或告警链路。
- 遗留风险：后端已返回 `deduped`，但前端如果不展示去重状态，用户仍会误以为又创建了一条候选。
- 下一轮建议：前端展示“已存在候选”，让重复提交结果和真实后端行为一致。

### 2026-05-17 Round 28：Run Trace 学习候选重复提交反馈

- 完成：前端 `SessionRunLearningCandidateResult` 补充 `deduped` 字段；Run Trace 学习预览弹窗在重复提交时显示“已存在候选”，按钮也同步进入已存在状态，避免误导用户继续重复操作。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，17 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：候选生成从“后端可去重”推进到“用户可感知去重”，减少学习治理队列里的重复和误操作。
- OpsCore 主线影响：只改前端反馈和类型，不新增配置、不改变候选状态机、不触碰资产、巡检、告警或审批执行。
- 遗留风险：学习候选详情仍分散在 Run Trace 弹窗和知识库候选池中，后续可以在满足当前功能后再考虑复用组件。
- 下一轮建议：停止继续打磨这个小功能，转向 `session_search` 或多 Agent 权限继承这类 Hermes 对标中更高价值的下一项。

### 2026-05-17 Round 29：session_search 最小只读接入

- 完成：`session_search` 从 Hermes adapter 的“未接入”错误升级为 OpsCore 原生只读会话搜索；工具会按查询词扫描会话消息、工具证据和 Run Trace，返回会话、消息、类型、摘要、run_id 和证据引用；工具中心同步从“未接入”改为“当前可用”。
- 验证：`python -m pytest tests/test_hermes_tool_adapter.py tests/test_tool_catalog_routes.py -q` 通过，13 passed；`python -m compileall core api scripts` 通过；`python scripts/check_tool_policies.py` 通过，63 tools。
- Hermes 差距变化：补上 Hermes 核心的 session recall 能力，但采用 OpsCore 的会话库、证据链和只读安全边界，不直接复制 Hermes 的 FTS/LLM 摘要路径。
- OpsCore 主线影响：只增加模型可调用的只读检索工具，不改变会话写入、审批、工具执行、资产、巡检或告警链路。
- 遗留风险：当前是 bounded scan，不是 SQLite FTS5/CJK trigram 索引；跨全部历史很多时性能和召回仍有限。
- 下一轮建议：功能满足即可先收手。后续若实际搜索慢或召回差，再单独做 FTS/CJK 索引和前端入口。

### 2026-05-17 Round 30：多 Agent 权限继承

- 完成：`dispatch_sub_agents` 的底层分发在调用子会话前计算最终权限：`父级允许读写 && 子会话允许读写`；父级全局/组模式切到只读时，下面子会话不会被分发为读写；结果里返回最终 `allow_modifications` 和 `session_mode`，便于审计。
- 验证：`python -m pytest tests/test_agent_task_dispatch.py tests/test_dispatcher_session_tools.py tests/test_agent_headless_setup.py -q` 通过，12 passed；`python -m compileall core api scripts` 通过。
- Hermes 差距变化：多 Agent 分发开始具备 OpsCore 自己的权限上限继承，不把 Hermes 的 delegate 作为无边界子任务复制进来。
- OpsCore 主线影响：只收紧分发权限上限，不改变工具执行、审批策略、资产连接、巡检或告警逻辑。
- 遗留风险：这只是后端分发层的最小闭环；前端全局模式/组模式的批量切换状态仍需要后续单独验收。
- 下一轮建议：功能满足先收手。后续再做前端组/全局模式显示和批量只读/读写切换的一致性。

### 2026-05-17 Round 31：多 Agent 分发结果前端可见

- 完成：`ToolTraceList` 对 `dispatch_sub_agents` 的 `BATCH_COMPLETE` 返回增加“协同子任务”摘要，展示每个子会话 ID、执行状态、最终只读/读写模式和错误/报告预览；只读继承结果在前端可直接看到。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑完整 preflight 和 staged audit。
- Hermes 差距变化：多 Agent delegate 不再只是后台执行结果，OpsCore 已能把子任务权限和结果放进同一条工具证据链，便于审计和复盘。
- OpsCore 主线影响：只读展示分发结果，不改执行、审批、资产、巡检、通知或告警逻辑。
- 遗留风险：全局模式/组模式的批量切换 UI 仍是独立验收项，本轮不继续扩展。
- 下一轮建议：该切片功能满足即可收手，后续转向更高价值的可观测、知识库或记忆治理缺口。

### 2026-05-17 Round 32：会话组权限批量切换

- 完成：会话组头部增加“全组只读 / 全组读写”动作，复用现有单会话权限 API 批量同步组内会话；前端先乐观更新，失败项会回退并提示。
- 验证：`python -m pytest tests/test_session_sidebar_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑完整 preflight 和 staged audit。
- Hermes 差距变化：多 Agent 组模式的权限上限不再只靠后台继承，操作员可以在会话组层面快速切换读/写边界。
- OpsCore 主线影响：只影响活跃会话前端权限切换和既有权限 API，不改变工具执行、审批策略、资产、巡检、通知或告警逻辑。
- 遗留风险：当前是前端批量调用单会话接口，不是后端事务；如果会话数量很大，后续再单独做后端批量接口。
- 下一轮建议：功能满足即可收手，后续再处理“全局模式”入口或转向可观测/记忆治理。

### 2026-05-17 Round 33：全局会话权限批量切换

- 完成：会话侧栏顶部增加“全部只读 / 全部读写”，复用同一批量同步函数作用于全部活跃会话；无活跃会话时只提示，不发请求。
- 验证：`python -m pytest tests/test_session_sidebar_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑完整 preflight 和 staged audit。
- Hermes 差距变化：全局模式和组模式都有直接入口，多 Agent 协同前可以先统一收紧或打开会话权限边界。
- OpsCore 主线影响：只影响前端活跃会话权限批量操作，不改变工具执行、审批、资产、巡检、通知或告警逻辑。
- 遗留风险：仍是前端逐会话调用；大量会话场景后续可补后端批量接口和进度条。
- 下一轮建议：权限切换这块已达到可用闭环，应收手，下一轮转向可观测/记忆治理。

### 2026-05-17 Round 34：可观测根因候选前端入口

- 完成：可观测排查卡片新增“生成根因候选”，复用现有后端 root-cause 接口，把当前证据链写入待复核根因候选；没有证据时只提示先追加证据。
- 验证：`python -m pytest tests/test_observability_frontend.py tests/test_observability_routes.py tests/test_observability_investigation.py -q`；`cd frontend && npm run build`；提交前继续跑完整 preflight 和 staged audit。
- Hermes 差距变化：可观测任务从“有任务和证据”推进到“能形成可复核根因候选”，更接近 Hermes 式 trace -> evidence -> hypothesis 的闭环。
- OpsCore 主线影响：只改可观测前端调用和展示入口，不自动处置、不触发工具执行、不改变资产、告警、巡检或审批链路。
- 遗留风险：候选内容仍是证据驱动的待复核草稿，不是模型自动排序；后续可接入 Summary Agent 生成更精细的候选。
- 下一轮建议：可观测这块先继续补“证据详情/根因候选状态”这类小闭环，不直接做复杂自动编排。

### 2026-05-17 Round 35：可观测根因候选状态可见

- 完成：可观测排查卡片里的根因候选从只显示标题和置信度，补为中文状态、支撑证据数、反证数和最多三条建议下一步；`open` 显示为“待复核”，`confirmed/rejected/watching` 分别显示为“已确认/已驳回/观察中”。
- 验证：`python -m pytest tests/test_observability_frontend.py tests/test_observability_routes.py tests/test_observability_investigation.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：可观测根因候选开始具备可读的 review 状态，用户能判断它只是候选、已确认还是被驳回，避免把待复核内容误当成结论。
- OpsCore 主线影响：纯前端只读展示，不新增状态修改接口，不触发工具执行、不改变资产、告警、巡检或审批链路。
- 遗留风险：状态流转仍缺少后端操作入口；按“功能满足即可收手”，本轮先只解决“看不懂候选状态”的问题。
- 下一轮建议：停止继续打磨根因候选卡片，转向可观测证据详情复用组件或记忆/知识库的更高价值缺口。

### 2026-05-17 Round 36：可观测证据详情展开

- 完成：可观测排查卡片的证据链新增“查看详情/收起详情”，展开后显示证据置信度、时间、`raw_ref` 和原始摘录，方便从根因候选回查证据来源。
- 验证：`python -m pytest tests/test_observability_frontend.py tests/test_observability_routes.py tests/test_observability_investigation.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：可观测从 summary 级证据展示推进到可展开的 source/excerpt 级证据回查，更接近 Hermes trace/log 可回放体验。
- OpsCore 主线影响：纯前端只读展开，不新增接口、不改变证据生成、不触发工具执行、不碰资产、告警、巡检或审批。
- 遗留风险：仍是页面内局部展开，不是跨知识库、Run Trace、报告共用的 EvidenceRef 组件；按“功能满足即可收手”，本轮先满足可看证据详情。
- 下一轮建议：停止继续打磨可观测卡片，转向记忆/知识库的更高价值缺口，或后续统一抽 EvidenceRef 组件。

### 2026-05-17 Round 37：学习候选辅助审核元数据

- 完成：Runbook/Skill 发布候选生成和质量清单保存时写入规则化辅助审核结果，包括 `accept / needs_human_review`、风险等级、缺失项和建议；知识库发布候选池和详情抽屉只读展示“辅助审核”。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：学习候选不再只靠人工看清单，开始具备辅助审核元数据，向 Hermes 式“经验先评估、再沉淀”的安全学习闭环靠近。
- OpsCore 主线影响：只增强候选池元数据和知识库展示，不调用真实模型、不自动批准、不自动发布、不影响资产、告警、巡检或工具执行。
- 遗留风险：当前是规则化审核，尚未接入真实辅助模型输出；按“功能满足即可收手”，本轮先让审核状态可存、可更新、可见。
- 下一轮建议：若继续学习治理，再做辅助模型审核接口；否则转向 Prompt 生命周期或 ContextEngine 这类架构缺口。

### 2026-05-17 Round 38：Prompt 模块清单进入 Run Trace

- 完成：聊天会话准备阶段生成 `prompt_modules` manifest，只记录模块名、版本、启用状态、资产类型和权限模式，不保存完整 prompt、Skill 内容、RAG 正文或密钥；Run Hook 上下文白名单携带该清单，后续 Run Trace 可审计本轮注入了哪些 prompt 模块。
- 验证：`python -m pytest tests/test_agent_prompts.py tests/test_agent_chat_setup.py tests/test_agent_chat_loop.py -q`；提交前继续跑 `python scripts/preflight.py --check-git`、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：Prompt 从“拼装后不可见”推进到“可审计模块生命周期”，接近 Hermes 的 prompt/context governance，同时保留 OpsCore 的脱敏和证据优先边界。
- OpsCore 主线影响：只增加运行上下文元数据，不改变 prompt 文本、不改变工具选择、不改变模型调用、不影响资产、告警、巡检或审批。
- 遗留风险：当前只覆盖 chat surface；headless/cron 后续可复用同一 manifest 思路，但本轮先收住，避免大范围重构。
- 下一轮建议：再做 headless prompt manifest 或 ContextEngine 最小接口，二选一推进。

### 2026-05-17 Round 39：Headless Prompt 模块清单

- 完成：后台无人值守 headless 执行准备阶段生成 `prompt_modules` manifest，记录 headless surface、资产类型、协议、读写模式、委派任务模块、工具目录和本地 Skill 路径可用性；Run Hook 上下文同步携带该清单。
- 验证：`python -m pytest tests/test_agent_prompts.py tests/test_agent_headless_setup.py tests/test_agent_headless_loop.py -q` 通过，19 passed，182 subtests。
- Hermes 差距变化：chat 和 headless 两条主要 Agent 入口都具备 Prompt 生命周期审计元数据，继续向 Hermes 式 context/prompt governance 靠拢，但不保存完整 prompt 内容。
- OpsCore 主线影响：只增加 headless 运行上下文元数据，不改变 prompt 文本、不改变工具执行、不改变审批 gate、不影响资产、告警、巡检或通知。
- 遗留风险：cron/巡检等上层任务若有独立运行记录，还需要后续在其调度记录里引用同一 manifest；本轮按“功能满足即可收手”先覆盖 headless 主路径。
- 下一轮建议：停止继续打磨 prompt manifest，转向 ContextEngine 最小只读接口或知识/记忆治理的下一处缺口。

### 2026-05-17 Round 40：ContextEngine 最小只读接口

- 完成：新增 `core/context_engine.py`，把聊天入口里的 LTM、知识库 RAG、资产画像和引用列表读取收束为 `ChatContextBundle`；`prepare_chat_agent_run` 只消费 bundle，不再直接关心各上下文来源的取数细节。
- 验证：`python -m pytest tests/test_context_engine.py tests/test_agent_chat_setup.py -q` 通过，7 passed。
- Hermes 差距变化：上下文来源从“散落在 chat setup 里”推进到“统一只读上下文包”，为后续记忆、知识库、Run Trace 和 prompt governance 解耦打基础。
- OpsCore 主线影响：不新增前端、不新增配置项、不改变 prompt 文本、不改变工具执行、不改变 LTM/RAG/画像读取策略、不影响资产、告警、巡检或审批。
- 遗留风险：当前 ContextEngine 只覆盖 chat 主路径；headless/cron/可观测若需要统一上下文，可后续逐条接入，不能一次性重构。
- 下一轮建议：功能满足先收手。后续可做 ContextEngine 的上下文来源审计元数据，或转向知识/记忆候选治理的下一处缺口。

### 2026-05-17 Round 41：ContextEngine 来源审计元数据

- 完成：`ChatContextBundle` 增加 `source_audit`，记录 `system_prompt / long_term_memory / knowledge_base / asset_profile` 的启用状态、是否命中、引用数量和读取状态；chat 运行上下文增加 `context_sources`，Run Hook 白名单同步带出。
- 验证：`python -m pytest tests/test_context_engine.py tests/test_agent_chat_setup.py tests/test_agent_chat_loop.py -q` 通过，29 passed。
- Hermes 差距变化：上下文不再只是最终拼进 prompt 的文本，运行记录能看到“本轮到底用了哪些上下文来源”，更接近 Hermes 式 context trace 和可复盘能力。
- OpsCore 主线影响：只记录来源级元数据，不保存 prompt 正文、RAG 正文、LTM 正文或资产画像正文；不改变工具执行、模型调用、审批、资产、告警或巡检。
- 遗留风险：当前只记录来源命中和引用数量，还没有统一展示页；按“功能满足即可收手”，本轮先把后端审计数据打通到 Run Hook。
- 下一轮建议：停止继续打磨 ContextEngine 元数据，转向知识/记忆候选治理，或做 Run Trace 前端轻量展示。

### 2026-05-17 Round 42：Run Trace 上下文来源轻量展示

- 完成：右侧 `AIOps Run Trace` 每次运行卡片从 `run:start` 事件读取 `context_sources`，以 chips 展示系统提示词、长期记忆、知识库和资产画像的命中状态、引用数量或读取失败状态。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，19 passed；`cd frontend && npm run build` 通过。
- Hermes 差距变化：后端已有 context trace 元数据，现在前端也能直接看到本轮上下文来源，减少“模型为什么这么判断”的黑盒感。
- OpsCore 主线影响：只改 Run Trace 前端展示，不新增后端接口，不展示 prompt/RAG/LTM/画像正文，不改变模型调用、工具执行、审批、资产、告警或巡检。
- 遗留风险：当前是卡片级轻量展示，不是完整上下文审计详情页；按“功能满足即可收手”，本轮只解决“看不到来源命中”的问题。
- 下一轮建议：停止继续打磨 Run Trace UI，转向知识/记忆候选治理或学习候选辅助模型审核接口。

### 2026-05-17 Round 43：学习候选辅助审核 Gate

- 完成：Runbook/Skill 学习候选进入 `approved` 或 `published` 前会基于当前质量清单刷新辅助审核结果，只有 `review.decision=accept` 且质量清单全部通过才允许继续；老数据或导入数据里的过期审核状态不能绕过 gate。
- 验证：`python -m pytest tests/test_file_memory_store.py -q` 通过，25 passed；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：学习闭环从“审核结果可展示”推进到“审核结果参与状态流转”，更接近 Hermes 式先评估、再沉淀、再发布的安全学习流程。
- OpsCore 主线影响：只约束学习候选状态机，不调用真实模型、不自动批准、不自动发布、不影响资产、告警、巡检、工具执行或通知。
- 遗留风险：当前辅助审核仍是规则化审核；后续如果接入辅助模型，应把模型输出归一到同一个 `review` 结构，继续走同一个 gate。
- 下一轮建议：本功能满足即可收手，下一步转向更高价值缺口，例如 Prompt/Context 审计的汇总页或知识候选的批量管理体验。

### 2026-05-17 Round 44：发布候选池筛选管理

- 完成：知识库发布候选池新增状态筛选、类型筛选、状态计数和“需补齐”标记；候选列表从固定前 8 条改为筛选后前 20 条，并显示当前筛选命中数量。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，19 passed；`cd frontend && npm run build` 通过；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：学习候选治理从“能审核和 gate”推进到“多候选时能快速定位待处理项”，更接近 Hermes 式候选池/任务池的运营体验。
- OpsCore 主线影响：只改知识库前端展示和筛选，不新增接口、不改变后端状态机、不自动批准、不影响资产、告警、巡检、工具执行或通知。
- 遗留风险：当前仍是前端内存筛选，候选上百上千时还需要后端分页和服务端过滤；按“功能满足即可收手”，本轮先解决几十条候选的可用性。
- 下一轮建议：停止继续打磨候选池 UI，下一步转向 Context/Prompt 汇总审计，或后续单独做服务端分页。

### 2026-05-17 Round 45：Run Trace Prompt 模块可见

- 完成：右侧 `AIOps Run Trace` 从 `run:start` 上下文读取 `prompt_modules` manifest，展示本轮启用的 Prompt 模块、surface 和 mode；只展示模块名与启用状态，不展示完整 prompt、RAG 正文、LTM 正文或密钥。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，20 passed；`cd frontend && npm run build` 通过；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：Prompt 生命周期审计从后端元数据推进到前端可见，用户能复盘本轮到底启用了哪些提示词模块，更接近 Hermes 式 prompt/context trace。
- OpsCore 主线影响：只改 Run Trace 前端展示，不新增接口、不改变 prompt 生成、不改变模型调用、不影响资产、告警、巡检、工具执行或审批。
- 遗留风险：当前仍是单次运行卡片级展示，不是全局 Prompt 审计报表；按“功能满足即可收手”，本轮只解决“已有 manifest 不可见”的问题。
- 下一轮建议：停止继续打磨 Run Trace 卡片，后续可转向全局 Prompt/Context 审计汇总或知识库服务端分页。

### 2026-05-17 Round 46：发布候选池服务端状态过滤

- 完成：`/knowledge/memory/learning-candidates` 新增 `statuses` 查询参数，`FileMemoryStore.list_learning_candidates` 在排序和 limit 前按状态过滤；前端 API 包装兼容旧调用，并支持传入发布候选状态列表。
- 验证：`python -m pytest tests/test_file_memory_store.py tests/test_knowledge_routes.py tests/test_tool_policy_runtime_frontend.py -q` 通过，63 passed；`cd frontend && npm run build` 通过；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：发布候选池从纯前端筛选推进到后端可过滤，为候选数量增长后的服务端分页/运营视图打基础。
- OpsCore 主线影响：只扩展只读列表查询，不改变候选状态机、不自动批准、不影响资产、告警、巡检、工具执行、审批或通知。
- 遗留风险：当前仍未做分页游标和服务端计数聚合；按“功能满足即可收手”，本轮只补最小过滤契约。
- 下一轮建议：停止继续打磨发布候选池，后续转向全局 Prompt/Context 审计汇总或记忆学习质量报表。

### 2026-05-17 Round 47：学习发布质量汇总

- 完成：记忆质量仪表盘新增“学习发布质量”只读汇总，统计 Runbook/Skill 发布候选总数、需补齐、可推进和已发布数量，并可跳转查看候选池。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q` 通过，21 passed；`cd frontend && npm run build` 通过；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：记忆质量页不再只看文件健康，也能看到学习沉淀链路是否堵在质量清单/辅助审核上，更接近 Hermes 式学习治理视角。
- OpsCore 主线影响：只读前端汇总，不新增接口、不改变状态机、不自动批准、不自动发布、不影响资产、告警、巡检、工具执行或审批。
- 遗留风险：当前统计来自前端已加载候选，不是后端聚合；按“功能满足即可收手”，本轮先让质量堵点可见。
- 下一轮建议：停止继续打磨记忆质量卡片，后续转向全局 Prompt/Context 审计汇总或服务端聚合报表。

### 2026-05-17 Round 48：Run Trace Context/Prompt 汇总条

- 完成：`AIOps Run Trace` 顶部新增 `Context/Prompt 审计` 汇总条，统计最近运行的上下文源数量、命中数量、读取失败数量和已启用 Prompt 模块数量。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：Context/Prompt 审计从单次运行卡片推进到最近运行的聚合视图，便于快速判断本轮上下文和提示词模块是否正常注入。
- OpsCore 主线影响：只读前端汇总，不新增接口、不展示 prompt 正文、不改变模型调用、不影响资产、告警、巡检、工具执行或审批。
- 遗留风险：当前聚合范围是前端最近 6 次运行，不是全局后端报表；按“功能满足即可收手”，本轮只补可见汇总。
- 下一轮建议：停止继续打磨 Run Trace 汇总条，后续转向更高价值的后端审计报表或工具执行策略可视化。

### 2026-05-17 Round 49：多 Agent 指令边界审计字段

- 完成：`dispatch_group_tasks` 的每个成功子任务结果新增 `permission_boundary`，记录 `scope`、父级模式、目标会话模式、最终执行模式、是否降权和降权原因。
- 验证：`python -m pytest tests/test_agent_task_dispatch.py -q`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 协同不再只返回最终 `readonly/readwrite`，而是能解释全局/组/会话权限如何合成，后续前端和 Run Trace 可以直接展示。
- OpsCore 主线影响：只增加后端返回审计字段，不改变实际权限计算，不扩大写权限，不影响告警、巡检、资产中心或工具注册。
- 遗留风险：当前只是结果字段，前端还没有完整展示全局/组/单会话边界；按“功能满足即可收手”，本轮只补执行结果可审计基础。
- 下一轮建议：在会话侧边栏或 Run Trace 中展示 `permission_boundary`，让用户能看到全局/组模式下哪些会话被降权。

### 2026-05-17 Round 50：协同子任务权限边界展示

- 完成：`ToolTraceList` 的协同子任务列表读取 `permission_boundary`，用小标签展示全局/组/会话边界、继承只读、目标只读或降权，并在 tooltip 中给出父级、目标和最终模式。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 协同从“只返回结果”推进到“能解释权限边界”，用户可以直接看到全局/组指令为什么没有放大到写权限。
- OpsCore 主线影响：只读前端展示，不改变调度、不改变权限、不改变工具执行，不碰告警、巡检、资产中心。
- 遗留风险：展示位置仍在工具 Trace 中，不是会话组顶部的全局权限看板；按“功能满足即可收手”，本轮只补协同结果可读性。
- 下一轮建议：阶段 2 暂停 UI 打磨，转向单会话覆盖/组继承的规则说明或后端审计聚合。

### 2026-05-17 Round 51：多 Agent 目标权限批量同步后端

- 完成：新增 `PUT /sessions/multi-agent/permissions`，支持 `scope=global/group`、`permission_mode=readonly/readwrite`、可选 `target_session_ids`，直接写回选中活跃会话的 `allow_modifications`。
- 验证：`python -m pytest tests/test_session_runtime.py tests/test_session_runtime_routes.py tests/test_api_mappers.py -q`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 从临时调度权限推进到实际会话状态同步，符合“全局/组切权限后，单独会话也统一改变”的产品规则。
- OpsCore 主线影响：仅新增后端基础能力；分组模式硬校验 `group_name`，组外目标只进入 `skipped_sessions`，不会被修改；不改变告警、巡检、资产中心或工具执行。
- 遗留风险：前端还没有接入目标选择器和执行前影响预览；本轮只补后端基础，避免 UI 和调度一次性耦合。
- 下一轮建议：做前端影响范围预览和权限同步按钮，再把多 Agent 任务下发只绑定到已选会话。

### 2026-05-18 Round 52：全局/分组权限按钮接入批量同步

- 完成：侧边栏现有 `全部只读/全部读写` 和 `全组只读/全组读写` 复用新的 `/sessions/multi-agent/permissions`，全局传 `scope=global`，分组传 `scope=group + group_name`。
- 验证：`python -m pytest tests/test_session_sidebar_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：前端权限切换不再逐个调用单会话接口，而是通过多 Agent 目标权限同步接口写回会话状态，符合全局/分组统一改变单独会话状态的规则。
- OpsCore 主线影响：保留单会话 `updatePermission` 作为失败回退和 TopBar 单会话切换；不改变多 Agent 任务下发、不碰告警、巡检或资产中心。
- 遗留风险：当前仍是全局全部或组内全部，尚未提供多选目标选择器和执行前预览；本轮只完成现有按钮的正确后端路径。
- 下一轮建议：增加全局/分组的目标多选与影响范围预览，再把任务下发绑定到已选目标。

### 2026-05-18 Round 53：全局/分组权限影响范围预览

- 完成：会话侧边栏全局权限按钮下方展示本次会影响的总会话数、只读数和读写数；分组权限按钮旁展示组内只读/读写分布，并在 tooltip 中给出完整影响范围。
- 验证：`python -m pytest tests/test_session_sidebar_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 权限从“可批量同步”推进到“执行前能看到影响面”，降低全局/组模式下盲切权限的风险。
- OpsCore 主线影响：只改会话侧边栏展示和统计，不新增接口、不改变权限同步语义、不改变多 Agent 任务下发，不碰告警、巡检、资产中心或 Hermes 参考目录。
- 遗留风险：当前仍是全局全部或组内全部的预览，还没有多选目标选择器；按“功能满足即可收手”，本轮只补最小影响面可见性。
- 下一轮建议：进入目标选择器前先确认业务需要；如果继续阶段 2，再做“全局/组模式指定某个或多个会话下发任务”的最小切片。

### 2026-05-18 Round 54：多 Agent 下发执行层分组边界

- 完成：会话上下文带出 `group_name/tags`；`list_active_sessions` 返回非敏感组名；`dispatch_sub_agents` 支持 `dispatch_scope=global/group` 和 `group_name`，分组模式下只允许向当前组内在线会话下发，组外目标直接返回 `group_mismatch`。
- 验证：`python -m pytest tests/test_agent_session_context.py tests/test_dispatcher_session_tools.py tests/test_tool_registry.py -q`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 不再只依赖前端按钮或模型自觉遵守范围，执行工具本身开始承载全局/分组边界，符合解耦且安全的 orchestration gate。
- OpsCore 主线影响：只改会话工具执行边界和工具 schema，不改变单会话工具、不改变读写权限合成、不改变告警、巡检、资产中心或 Hermes 参考目录。
- 遗留风险：当前仍由模型通过 `dispatch_sub_agents` 提供任务列表，还没有前端多选下发面板；按“功能满足即可收手”，本轮先把执行层边界做硬。
- 下一轮建议：如果继续阶段 2，再做轻量前端“选中会话并生成多 Agent 任务”的入口；否则转向可观测/知识/审批的更高优先级缺口。

### 2026-05-18 Round 55：多 Agent 目标选择与指令草稿

- 完成：会话侧边栏支持勾选多 Agent 目标、按会话组一键选择目标，并在顶部显示已选目标数量和推断出的全局/分组范围；点击“生成指令”会把包含 `dispatch_scope/group_name/target_session_id` 的协同任务草稿写入当前聊天输入框。
- 验证：`python -m pytest tests/test_session_sidebar_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：多 Agent 从“模型自己查会话并下发”推进到“用户能明确选定目标，模型按明确目标调用工具”，更接近可控编排和安全确认。
- OpsCore 主线影响：只生成聊天草稿，不自动发送、不直接执行任务、不新增调度 API；仍由聊天执行层的 `dispatch_sub_agents` gate 保证全局/分组边界，不影响告警、巡检、资产中心或 Hermes 参考目录。
- 遗留风险：当前是草稿入口，不是完整任务编排面板；按“功能满足即可收手”，先保证目标选择和人工确认闭环。
- 下一轮建议：阶段 2 可以在这里收手；后续若用户确认体验足够，再考虑任务模板或运行结果聚合，不继续无止境打磨。

### 2026-05-18 Round 56：审批中心风险筛选

- 完成：审批中心在状态筛选之外新增风险类型筛选和搜索框，可按破坏性、外发/通知、写入变更、技能变更快速定位审批记录；审批列表显示当前命中数/状态总数。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：审批从单纯队列推进到可运营的风险视图，用户在审批很多时可以先处理最高风险项。
- OpsCore 主线影响：只做前端本地筛选，不改审批 API、不改审批决策、不改执行 gate，不影响告警、巡检、资产中心或 Hermes 参考目录。
- 遗留风险：当前筛选基于已加载的状态页数据，不是服务端分页/聚合；按“功能满足即可收手”，先解决几十到几百条审批的定位问题。
- 下一轮建议：如果审批量继续增长，再做服务端分页和聚合；当前先转向可观测、知识或记忆治理的下一处短板。

### 2026-05-18 Round 57：学习候选统一搜索

- 完成：知识库 AI 记忆的学习候选区新增统一搜索框，同时过滤待确认候选、Runbook/Skill 候选和发布候选池；可按候选 ID、摘要、来源会话、证据、状态、辅助审核和状态事件快速定位。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：学习治理从“能分流和发布”推进到“候选多了也能找得到”，更接近 Hermes 式候选池/学习队列的可运营体验。
- OpsCore 主线影响：只改知识库前端本地筛选，不改候选状态机、不改记忆写入、不自动发布 Runbook/Skill，不影响告警、巡检、资产中心或 Hermes 参考目录。
- 遗留风险：当前仍是本地已加载候选搜索，不是服务端分页/全文索引；按“功能满足即可收手”，先满足几十到几百条候选的定位需求。
- 下一轮建议：停止继续打磨候选列表。后续转向可观测证据统一组件、Context/Prompt 审计汇总，或在实际数据量变大后再做服务端搜索分页。

### 2026-05-18 Round 58：证据引用按钮复用

- 完成：新增 `EvidenceReferenceChip`，Run Trace 事件里的证据/审批引用和知识库学习候选里的工具证据引用统一使用同一个引用按钮组件。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：前端开始把 trace、审批和学习候选的引用入口收束为可复用 UI，后续做统一证据详情、报告引用和可观测证据回查时不会继续复制按钮样式和语义。
- OpsCore 主线影响：只抽取前端展示组件，不改证据查询 API、不改审批 API、不改变工具执行、告警、巡检或资产中心。
- 遗留风险：当前只统一“引用入口按钮”，详情弹窗仍保留在各自页面内；按“功能满足即可收手”，本轮不继续扩大到跨页面弹窗重构。
- 下一轮建议：停止继续拆 UI 组件。后续更高价值方向是 Context/Prompt 审计汇总页，或可观测证据与 Run Trace 的统一详情查询接口。

### 2026-05-18 Round 59：Run Trace 审计覆盖提示

- 完成：Run Trace 的 Context/Prompt 审计汇总新增“未审计”计数，明确显示最近运行中哪些 run 没有 context sources 或 prompt manifest。
- 验证：`python -m pytest tests/test_tool_policy_runtime_frontend.py -q`；`cd frontend && npm run build`；提交前继续跑 preflight、staged audit 和 GitNexus staged detect。
- Hermes 差距变化：审计面板不再只展示已有审计数据，也能暴露旧运行或未接入路径的审计缺口，避免用户误判所有运行都已纳入 prompt/context 治理。
- OpsCore 主线影响：只改 Run Trace 前端汇总展示，不改 hook payload、不改 ContextEngine、不改 prompt 构建、不影响告警、巡检或资产中心。
- 遗留风险：当前是前端根据已加载事件判断覆盖情况，不是服务端审计报表；按“功能满足即可收手”，先满足会话内最近运行的缺口可见。
- 下一轮建议：停止继续打磨 Run Trace 小标签。后续若继续做治理，应转向服务端 Context/Prompt 审计聚合或可观测证据统一查询。
