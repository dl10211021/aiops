# OpsCore 冒烟验收清单

日期：2026-05-15

## 目的

这份清单用于每次提交或继续优化前后做快速验收，避免在没有明确目标的情况下继续扩大修改范围。

当前优先验证运行策略主链路：

- 工具目录暴露运行策略。
- 会话工具接口带运行策略。
- 前端工具中心能展示策略。
- 审批中心能承接受控工具。
- 后端 preflight 和工作区审计通过。

## 禁止顺手修改范围

除非用户明确重新打开这些方向，否则冒烟验收期间不修改：

- 告警功能。
- 资产中心整合。
- 巡检功能。
- 统一扩展协议。
- `.research/hermes-agent/`。

## 基础环境

项目根目录：

```powershell
cd "D:\AIOPS\skillops - 20260225"
```

确认工作区：

```powershell
git status --short --branch
git log -3 --oneline --decorate
```

通过标准：

- 分支为 `master`。
- 本地与 `origin/master` 同步，或只领先明确待提交的本轮改动。
- 无未知生成物、运行文件、敏感文件被混入。

## 服务健康

确认本地服务：

```powershell
@'
import json
from urllib.request import urlopen
for url in ["http://127.0.0.1:8000/healthz", "http://localhost:8000/healthz"]:
    payload = json.loads(urlopen(url, timeout=10).read().decode("utf-8"))
    print(url, payload.get("status"), payload.get("checks", {}).get("hydrate"))
'@ | python -
```

通过标准：

- 两个地址都返回 `ok`。
- `hydrate.running=false`。
- `hydrate.done == hydrate.total`。

## 工具中心 API

检查工具中心策略字段：

```powershell
@'
import json
from urllib.request import urlopen
data = json.loads(urlopen("http://127.0.0.1:8000/api/v1/tools/center", timeout=10).read().decode("utf-8"))["data"]
tools = {
    tool["name"]: tool
    for toolset in data["toolsets"]
    for tool in toolset["tools"]
}
for name in ["linux_execute_command", "db_execute_query", "write_file", "send_notification", "skills_list", "skill_view"]:
    item = tools.get(name)
    if not item:
        print(name, "MISSING")
        continue
    print(json.dumps({
        "name": name,
        "operation_mode": item.get("operation_mode"),
        "approval_policy": item.get("approval_policy"),
        "destructive": item.get("destructive"),
        "concurrency_safe": item.get("concurrency_safe"),
        "timeout_policy": item.get("timeout_policy"),
        "retry_policy": item.get("retry_policy"),
    }, ensure_ascii=False))
'@ | python -
```

通过标准：

- `linux_execute_command` 是 `read_write / guarded_write`。
- `write_file` 是 `write / always_required`。
- `send_notification` 是 `external_effect / guarded_write`。
- `skills_list` 和 `skill_view` 是 `read / none`，且 `destructive=false`。
- 所有样本都有 `timeout_policy` 和 `retry_policy`。

## 会话工具 API

抽查活跃会话的工具策略完整性：

```powershell
@'
import json
from urllib.request import urlopen
base = "http://127.0.0.1:8000"
sessions = json.loads(urlopen(base + "/api/v1/sessions/active", timeout=10).read().decode("utf-8"))["data"]["sessions"]
missing = []
summary = []
for sid in list(sessions)[:10]:
    data = json.loads(urlopen(base + f"/api/v1/session/{sid}/tools", timeout=10).read().decode("utf-8"))["data"]
    details = data.get("active_tool_details") or []
    with_policy = 0
    for item in details:
        ok = item.get("operation_mode") and item.get("approval_policy") and item.get("timeout_policy") and item.get("retry_policy")
        if ok:
            with_policy += 1
        else:
            missing.append({"sid": sid, "tool": item.get("name")})
    summary.append({
        "sid": sid,
        "protocol": data.get("context", {}).get("protocol"),
        "total": len(details),
        "with_policy": with_policy,
    })
print(json.dumps({"summary": summary, "missing": missing[:20], "missing_count": len(missing)}, ensure_ascii=False, indent=2))
'@ | python -
```

通过标准：

- `missing_count=0`。
- 每个抽查会话的 `with_policy == total`。

## 前端页面

浏览器打开：

- `http://127.0.0.1:8000/#/tools`
- `http://127.0.0.1:8000/#/approvals`

工具中心通过标准：

- 页面能加载。
- 能看到工具总数和工具列表。
- `Linux/Unix 命令` 或 `linux_execute_command` 可见。
- 策略标签显示 `读写受控`、`写入受控` 等中文状态。
- 当前筛选样本不出现 `未知`。

审批中心通过标准：

- 页面能加载。
- 能看到审批队列或历史审批记录。
- 审批记录能展示策略来源、策略字段或运行结果。

## 自动化门禁

提交前必须执行：

```powershell
python scripts/worktree_audit.py --check-staged
python scripts/preflight.py --check-git
```

通过标准：

- `worktree_audit` 不报告 generated、runtime、sensitive、external-source 混入。
- `preflight passed`。
- 后端测试、编译、工具策略检查、runtime policy coverage、密钥扫描、依赖检查、前端 audit、前端 build 均通过。

## GitNexus 检查

提交前执行变更影响检查：

```text
gitnexus_detect_changes(scope="staged")
```

通过标准：

- 影响范围与本轮目标一致。
- 如果风险为 HIGH 或 CRITICAL，必须确认原因是目标链路本身，而不是误改其它模块。

## 当前已知可接受提示

以下输出当前可接受，不作为失败：

- Windows 下 Git 提示 LF 将被替换为 CRLF。
- 前端 build 提示部分 chunk 超过 500 kB。
- 测试中的预期错误日志，例如 disk full、隔离策略拒绝、模拟连接超时。

## 失败处理规则

冒烟失败时按这个顺序处理：

1. 先定位失败属于环境、旧进程、测试夹具还是代码回归。
2. 如果是旧进程，重启 `uvicorn main:app` 后重新验证。
3. 如果是代码回归，只修复本轮目标相关文件。
4. 不借冒烟失败顺手改告警、资产、巡检或扩展协议。
5. 修复后重新跑针对性测试、`worktree_audit`、`preflight`。

