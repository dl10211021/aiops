# OpsCore Agent Runtime 与运维 OP 提示词优化

日期：2026-05-13

## 背景

本次优化结合三类输入：

- OpsCore 当前实现：资产中心、会话上下文、原生协议工具、巡检计划、通知、报告、工具证据。
- `CC_notes(1)` 对 Claude Code 工程体系的源码解析：Prompt/Tool/Transcript/Subagent/Plugin/MCP/Slash Command 都是运行时能力图的一部分。
- Claude Code 公开文档中的通用工程原则：项目记忆、上下文管理、subagent 隔离、权限策略、hooks 和可验证任务。

结论：OpsCore 不应照搬代码助手的提示词，而应把其运行时思想转成 AIOps 运维平台自己的 OP Runtime。

## 当前优化

本轮先落地低风险第一层：Prompt Pack 与 Agent profile 清理。

### Prompt Pack

新增 `core/prompt_packs.py`，把原先混在 `core/agent_prompts.py` 里的大块提示词拆成可组合模块：

- `render_permission_mode_prompt`：只读/读写权限模式。
- `render_ops_runbook_prompt`：OpsCore 运维 OP 流程。
- `render_evidence_contract_prompt`：工具证据契约。
- `render_aiops_behavior_prompt`：AIOps 专家行为准则。
- `render_skill_install_prompt`：Skill 联网安装流程。
- `render_web_browser_prompt`：联网资料研究流程。
- `render_context_precedence_prompt`：上下文优先级。

`render_chat_system_prompt` 与 `render_headless_system_prompt` 的函数签名保持不变，降低对 chat/headless 主链路的影响。

### 运维 OP 流程

统一提示模型按以下路径工作：

```text
接收问题
-> 判断 OP 类型
-> 绑定资产/业务系统/会话
-> 生成只读计划
-> 调用原生协议工具采集证据
-> 形成风险判断和评分
-> 必要时追加验证
-> 生成 Markdown + HTML 报告
-> 发送通知并记录通知结果
-> 写入运行事件流和可追溯报告
```

第一版 OP 类型：

- 资料查询
- 只读巡检
- 故障排查
- 变更操作
- 报告/通知
- 技能安装
- 未知请求

### 证据契约

模型必须遵守：

- 没有当前轮次的原生协议工具结果，不输出“已巡检完成”“系统正常”“根因是”等结论。
- 每个关键判断必须对应工具结果、RAG 资料、资产画像或用户提供事实。
- 工具失败、认证失败、超时、连接不可达也是证据，不能隐藏。
- 多资产问题必须区分已验证资产、推测相关资产、未知资产。

## Agent Profile 清理

`workspaces/*/SOUL.md` 从人格文案调整为运维 OP 角色边界：

- `default`：通用运维 OP 执行者。
- `dba`：数据库原生协议优先，不再假设 SSH。
- `monitor`：可观测来源优先，不再假设本地脚本或旧路径。
- `security`：零侵入安全审计，不再假设 SSH。
- `master`：跨域编排，明确已验证/推测/未知节点。

## 后续 P0

1. `AIOpsRunTranscript`
   - 已新增 `core/aiops_run_transcript.py`，提供追加式 JSONL 运行事件存储。
   - 巡检运行现在会在创建、更新、嵌入事件追加和删除时同步维护 `inspection_run_transcripts/`。
   - 巡检报告新增 `transcript` 字段，用于后续运行恢复、报告重建、审计追踪和通知复盘。
   - 下一步应把工具调用、审批、通知发送、HTML 报告生成也写成同一类 transcript 事件。

2. `TaskRuntime`
   - 已新增 `core/aiops_task_runtime.py`，提供任务运行态快照、进度、当前阶段、当前目标、取消请求和运行耗时。
   - 巡检后台运行态已从裸 `_RUNNING_INSPECTIONS` dict 升级为兼容旧 dict 的 `AIOpsTaskRuntime`。
   - `run_state` 现在可返回 `task_status`、`current_stage`、`current_target`、`progress_current`、`progress_total`、`progress_percent`、`elapsed_ms`、`cancel_requested_at` 和 `runtime_message`。
   - 巡检计划卡片已接入运行态进度条，显示当前阶段、进度百分比、当前目标和运行时长。
   - 巡检报告弹窗已新增“运行时间线”视图，优先展示 transcript 事件流，并在老报告缺少 transcript 时降级展示原有进度事件。
   - 巡检页已新增“报告中心”，可从全局查看最近巡检报告、按状态筛选、搜索报告/计划/主机/通知结果，并直接查看或删除报告。
   - 报告中心已从前端本地筛选升级为 `/inspection-runs` 服务端分页、搜索和状态筛选，接口同时返回 `pagination` 与 `metrics`，避免报告数量上来后一次性拉取过多数据。
   - 报告中心已支持当前页多选、批量删除和清空选择；运行中报告不可勾选删除，避免误删正在写入的运行记录。
   - 报告中心已新增“归档策略预览”，按“每个计划保留最近 N 份”和“早于 N 天”生成 dry-run 清理建议，展示建议清理数量、跳过运行中数量和估算释放空间，但不执行删除。
   - 巡检计划列表已支持当前筛选页多选、批量暂停、批量恢复、批量删除；批量删除会阻止包含正在巡检任务的选择，避免误删运行中计划。
   - 取消当前巡检已改为确认弹窗，弹窗展示运行编号、阶段、当前目标、进度、运行状态和运行时长，避免误点后直接中断后台任务。
   - 下一步应把这些字段继续接入跨页批量任务策略和报告归档策略。

3. `ToolDefinitionV2`
   - 已在现有 `ToolDefinition` 上补充 `operation_mode`、`destructive`、`concurrency_safe`、`timeout_policy`、`approval_policy`、`evidence_family`、`ui_renderer`、`result_store_policy`、`retry_policy`、`metadata_version` 和 `runtime_scope`。
   - 这些字段目前是运行时目录元数据，不改变工具注册、工具暴露和执行逻辑；它们用于后续让模型、工具中心、审批、审计、报告渲染和并发调度共享同一份工具能力边界。
   - `/tools/catalog`、会话工具目录和工具中心都会返回同一组元数据；受控但未暴露给模型的内置工具也会带上相同策略字段，例如 `write_file` 标记为 `operation_mode=write`、`approval_policy=always_required`。
   - Agent 可读工具说明已接入这些边界：`prompt_lines` 会保留中文工具名和原始 tool id，同时追加“模式 / 审批 / 证据”摘要，例如 Linux 命令会标记为“读写受控、写入受控、主机命令证据”，数据库 SQL 会标记为“读写受控、写入受控、数据库证据”。
   - 工具阻断响应已附带 `tool_policy`，保留 `operation_mode`、`approval_policy`、`evidence_family` 等字段；SSE 工具轨迹会把这段策略元数据写入 `result_meta`，用于前端解释、审计和后续报告归因。
   - 普通成功/失败工具结束事件也会补齐 `tool_policy`，并同步写入工具证据的 `result_meta`，让命令、SQL、API 查询等执行记录都能按工具模式、审批策略和证据类型归类。
   - 会话消息中的工具执行轨迹已展示 `tool_policy`：当工具执行结束后，前端会展示“工具策略”块，标明只读/读写受控/写入、审批要求、证据类型和破坏性标记。
   - AI 思考链侧栏也会读取 `result_meta.tool_policy` 和证据内的 `result_meta.tool_policy`，每步工具轨迹显示策略标签，并支持按 `读写受控`、`数据库证据`、`主机命令证据` 等关键字检索。
   - 工具开始事件和审批请求事件也会携带 `tool_policy`，前端在工具仍处于运行中、或等待人工审批时即可展示工具模式、审批策略和证据类型，不必等到工具执行结束。
   - 工具 start/end 合并时会保留已有 `resultMeta`：结束事件的同名字段优先，但不会丢弃开始事件里已经写入的 `tool_policy`；前端流式合并和后端 trace collector 都按这个规则处理。
   - 工具 trace 现在贯穿 `toolCallId`：SSE 工具开始事件、后端 trace collector、前端流式合并和工具轨迹卡片都能看到同一个调用 ID；start/end 合并会优先按调用 ID 匹配，避免多工具交错时把结果合并到错误的运行项。
   - 审批中心列表、审批确认弹窗、会话审批卡片和工具轨迹卡片已统一复用同一套策略展示 helper，避免“读写受控 / 强制审批 / 数据库证据”等标签在不同页面翻译不一致。
   - 旧会话历史兼容层在重建 `exec_trace` 时也会按工具名补齐 `resultMeta.tool_policy`，避免历史会话重新打开后缺少策略标签。
   - 会话 Markdown 导出会在每个工具 Step 下输出 `Policy` 和 `Evidence` 行，离线报告中也能看到工具模式、审批策略、证据类型和证据编号。
   - 会话 retention 摘要会保留工具结果中的 `tool_policy`；删除压缩历史的审计摘要会记录工具名、证据编号和策略三元组，避免长期清理后审计断链。
   - 会话 Webhook 的 `summary` 模式会从完整 Markdown 中抽取执行审计摘要，优先带上 Step、Policy 和 Evidence，避免普通正文截断后外部通知丢失工具策略链路。
   - 辅助审查模型的 trace review prompt 和成功执行经验记忆都会写入策略三元组和证据编号，避免模型复盘、风险建议和会话级成功经验脱离工具审计链。
   - 资产画像生成的最近会话摘要会纳入工具轨迹行，包含工具名、状态、策略三元组、证据编号、执行摘要和结果摘要，避免画像模型只看自然语言回复而忽略实际工具证据。
   - 达到 Agent 步数保护上限时，阶段性报告生成会额外注入工具审计上下文，包含已完成工具的策略三元组、证据编号、执行摘要和结果摘要，避免上限报告脱离真实工具轨迹。
   - `core/tool_trace_policy.py` 已集中封装 `resultMeta` / `evidence.result_meta` / 工具注册表 fallback 的策略读取规则，以及证据编号和策略三元组格式化；AI trace、step-limit 摘要、会话导出、资产画像和 retention 审计都复用同一套 helper，减少字段漂移风险。
   - 工具中心已支持按状态、运行模式和审批策略筛选工具，搜索也会匹配 `operation_mode`、`approval_policy` 和 `evidence_family`，便于快速找到只读工具、读写受控工具、强制审批工具或暂未接入能力。
   - 审批请求记录已写入 `metadata.tool_policy`，审批中心会展示工具模式、审批策略、证据类型和结果保存策略。旧审批记录没有该字段时仍按原样展示。
   - 后续可以把这些元数据接入执行层：只读工具允许自动重试，写入/外发工具进入审批或确认，破坏性工具默认强制阻断，多资产并发只选择 `concurrency_safe=true` 的工具。

4. 巡检运行态升级
   - “立即巡检”不再只是触发函数，而是创建任务、写事件、展示进度、支持取消、落报告、发通知并记录通知结果。

## 不做的事

- 不复制 Claude Code 的泄露或疑似非公开提示词原文。
- 不把 OpsCore 做成代码助手。
- 不修改告警模块；该模块当前由其他人开发。
- 不把本地脚本作为真实资产巡检的默认路径。
