# OpsCore 冒烟验收结果

日期：2026-05-15

依据清单：`docs/architecture/2026-05-15-opscore-smoke-checklist.md`

## 结论

本次冒烟验收通过。

当前 `master` 与 `origin/master` 同步，运行中的本地服务能正常响应，工具中心、会话工具接口和审批中心均能消费运行策略元数据。

## Git 状态

执行：

```powershell
git status --short --branch
```

结果：

```text
## master...origin/master
```

结论：通过。

## 服务健康

检查地址：

- `http://127.0.0.1:8000/healthz`
- `http://localhost:8000/healthz`

结果：

| 地址 | 状态 | hydrate |
| --- | --- | --- |
| `127.0.0.1:8000` | `ok` | total=26, done=26, success=26, running=false |
| `localhost:8000` | `ok` | total=26, done=26, success=26, running=false |

结论：通过。

## 工具中心 API

接口：

```text
GET /api/v1/tools/center
```

工具目录摘要：

| 指标 | 数量 |
| --- | ---: |
| total | 73 |
| available | 62 |
| controlled | 9 |
| not_wired | 2 |

关键样本：

| 工具 | operation_mode | approval_policy | destructive | timeout | retry |
| --- | --- | --- | --- | --- | --- |
| `linux_execute_command` | `read_write` | `guarded_write` | false | 120/600 | 1 |
| `db_execute_query` | `read_write` | `guarded_write` | false | 60/300 | 1 |
| `write_file` | `write` | `always_required` | false | 60/300 | 1 |
| `send_notification` | `external_effect` | `guarded_write` | false | 45/180 | 1 |
| `skills_list` | `read` | `none` | false | 60/300 | 1 |
| `skill_view` | `read` | `none` | false | 60/300 | 1 |

结论：通过。

## 会话工具 API

接口：

```text
GET /api/v1/session/{session_id}/tools
```

抽查前 10 个活跃会话：

| 协议 | 工具数 | 带策略工具数 |
| --- | ---: | ---: |
| ssh | 31 | 31 |
| http_api | 31 | 31 |
| http_api | 31 | 31 |
| http_api | 31 | 31 |
| ssh | 31 | 31 |
| winrm | 31 | 31 |
| ssh | 31 | 31 |
| ssh | 31 | 31 |
| ssh | 31 | 31 |
| postgresql | 31 | 31 |

缺失策略字段数量：0。

结论：通过。

## 前端页面

验证页面：

- `http://127.0.0.1:8000/#/tools`
- `http://127.0.0.1:8000/#/approvals`

工具中心结果：

- 页面加载成功。
- 工具总数可见。
- `Linux/Unix 命令` 或 `linux_execute_command` 可见。
- `读写受控`、`写入受控` 等策略标签可见。
- 当前样本未出现 `未知`。

审批中心结果：

- 页面加载成功。
- 审批中心可见。
- 待审批或历史审批入口可见。
- 策略相关文本可见。

结论：通过。

## 未执行项

本次没有执行真实工具调用。

原因：

- 当前目标是主干冒烟，不触碰真实资产。
- 巡检方向当前已暂停。
- 告警方向由其他人开发，未纳入本次验收。
- 资产中心方向暂时搁置。

## 后续建议

后续继续开发前，优先选择明确产品目标，不建议在运行策略链路上继续无边界追加修复。

可选下一步：

- 会话窗口里把工具策略展示做得更直观。
- 针对一个只读工具做安全的端到端演示。
- 对前端 chunk 体积做独立性能优化切片。

