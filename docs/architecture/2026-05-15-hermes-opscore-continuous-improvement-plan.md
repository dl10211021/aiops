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
