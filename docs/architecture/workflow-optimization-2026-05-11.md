# OpsCore 工作流优化边界

日期：2026-05-11

## 当前主链路

OpsCore 的核心工作流应保持为：

```text
资产中心
-> 会话上下文
-> 结构化执行意图
-> 安全策略与审批
-> 原生协议工具 / Skills
-> 工具证据
-> AI 结论
-> 会话历史 / 长期记忆 / 可观测调查
```

其中“执行意图”和“工具证据”是跨会话、Skills、资产、可观测模块的共享契约，不应继续散落在 UI 文案或单个工具事件里。

## 已落地的优化

- 目录类数据采用短 TTL 缓存，避免技能市场、资产类型、数据库驱动能力在页面生命周期内永久过期。
- 数据库驱动能力和 Oracle Client 探测接口支持 `refresh=true`，便于安装驱动或变更环境变量后主动刷新。
- Chat Loop 引入结构化 `ExecutionIntent`，兼容原有中文关键词，但允许快捷指令、会话动作和可观测调查直接声明 `requires_live_evidence`。

## 可观测分支合流规则

当前主分支已经有可观测页面和 API 入口，`feat-observability-ai-troubleshooting` 分支还有更细分的后端服务边界。后续合流必须按下面规则处理：

1. **主分支保留**：前端 `ObservabilityCenter`、导航入口、现有 API 路由挂载。
2. **候选迁入**：观测分支中的 profile、source、evidence、investigation、topology 服务边界。
3. **禁止继续并行**：不要同时维护 `core/observability/service.py` 聚合实现和多服务实现的两套业务逻辑。
4. **合流顺序**：先迁移模型和持久化边界，再迁移 API，再让前端按同一 API contract 调整。
5. **验收标准**：资产绑定、会话绑定、调查创建、证据追加、根因候选都必须通过同一套服务和测试。

## 统一证据对象

后续应把 chat trace、session history、approval execution、observability evidence 统一到同一个逻辑对象：

```text
ToolEvidence
- evidence_id
- session_id
- investigation_id?
- asset_ref
- tool_name
- tool_family
- input_summary
- redacted_input
- output_preview
- result_status
- result_meta
- approval_ref?
- started_at
- finished_at
```

落地顺序：

1. 保持当前 `exec_trace` 兼容字段不变。
2. 在生成 `tool_end` 时补齐 `result_meta` 和可选 `evidence_id`。
3. 会话历史继续读取旧字段，但优先展示 `ToolEvidence` 字段。
4. 可观测调查追加证据时复用同一对象，不再复制一份只属于观测模块的证据结构。

## Dispatcher 收敛方向

`core/dispatcher.py` 后续只保留门面职责：

```text
dispatcher.py
-> ToolExecutionRouter
-> ApprovalGate
-> SkillRegistryService
-> SkillEvolutionService
```

新功能优先落到这些服务里，不继续扩大 dispatcher 单文件职责。拆分时必须保持现有工具名和响应形状兼容。
