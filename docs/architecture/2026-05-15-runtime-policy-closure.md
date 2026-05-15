# OpsCore Runtime Policy 优化收束记录

日期：2026-05-15

## 结论

本轮执行层优化先在这里收束，不再继续做无边界的“顺手修复”。

当前主线已经完成：

- 工具目录统一暴露 `operation_mode`、`approval_policy`、`destructive`、`concurrency_safe`、`timeout_policy`、`retry_policy` 等运行策略元数据。
- Agent 执行层已接入运行策略 gate：破坏性、外发、强制审批工具不会只依赖旧 safety policy。
- 工具执行已接入超时和重试策略，并把 attempts、retry_on、timeout_seconds、final_status、error_type 等元数据写入运行结果。
- 多工具并发已按 `concurrency_safe` 选择，只允许安全只读工具自动并发，写入、外发、破坏性和需要审批的工具保持串行或进入审批。
- 工具 start/end、SSE trace、AI 思考链、工具轨迹、会话导出、retention 审计、Webhook 摘要和旧会话兼容层均能保留或补齐工具策略。
- 旧 `/execute` 命令链路也会返回结构化运行策略错误，避免超时、重试失败、工具错误只剩普通字符串。
- 前端 HTTP 客户端已能识别结构化 `error_type`，并按认证、连接/超时、限流、审批、策略、执行、内部错误分类。

## 已验证

本轮多个切片均按项目门禁执行：

- `python scripts/worktree_audit.py --check-staged`
- `python scripts/preflight.py --check-git`
- GitNexus staged 影响检查
- 前端 `npm run build`
- 相关目标测试

最新状态：`master` 已提交并推送，工作区干净。

## 停止继续补丁的原因

后续继续在这条线上追加小修，收益会明显下降：

- 执行策略主链路已经闭环，再继续容易变成 UI 文案、分类枚举、边角状态的局部补丁。
- 告警功能当前由其他人开发，不能继续顺手改。
- 资产中心方向已被用户要求暂时搁置。
- 巡检功能已被用户要求先跳过。
- 全局 HTTP 客户端、Agent 执行环和工具策略都是高影响面区域，继续改动需要明确验收目标，而不是“继续”式扩散。

因此本记录之后，默认不再继续 runtime policy 代码改动，除非有明确缺陷、明确验收失败或新的产品需求。

## 产品级验收建议

下一步不应继续写代码，而应做一次真实链路验收：

1. 只读工具成功执行
   - 预期：不要求审批，可显示工具策略、证据类型、运行结果。

2. 读写受控工具命中安全策略
   - 预期：进入审批，审批卡片显示工具模式、审批策略、证据类型。

3. 破坏性工具调用
   - 预期：强制审批或阻断，不被自动执行。

4. 超时工具
   - 预期：返回 `tool_timeout`，前端归类为连接/执行超时，trace 显示 timeout_seconds 和 attempts。

5. 可重试只读工具
   - 预期：按 retry_policy 重试，最终 trace 显示 retried、attempts、retry_on。

6. 多只读工具并发
   - 预期：只有 `concurrency_safe=true` 且无需审批的工具自动并发。

7. 写入/外发工具混在多工具调用中
   - 预期：不会被自动并发；串行执行或进入审批。

8. 旧 `/execute` 路径
   - 预期：超时或运行策略失败时返回结构化 detail，前端可显示错误类别和原始 runtime_policy。

## 后续优先级

P0：先做产品级验收，不新增代码。

可用快速验收命令：

```powershell
python scripts/runtime_policy_smoke.py
```

该命令只跑运行策略相关的聚焦用例，覆盖强制审批、超时结构化错误、重试元数据、只读并发和混合批次串行/审批边界。完整发布前仍以 `python scripts/preflight.py --check-git` 为准。

P1：如验收发现实际体验问题，再按明确问题开小切片修复。

P2：如果需要继续增强，可考虑：

- 给运行策略错误增加统一用户提示组件。
- 在工具中心增加“策略健康检查”视图。
- 在会话 trace 中增加按错误类别筛选。
- 给生产环境配置单独的默认 timeout/retry 上限。

## 明确不做

- 不继续扩展统一扩展协议，该方向已取消。
- 不继续资产中心整合，该方向暂时搁置。
- 不继续巡检功能修复，该方向当前先跳过。
- 不改告警模块，避免与其他开发工作冲突。
