---
name: windows_security_log_troubleshooting
description: 通过 Kibana HTTP API 对 ES 中 winlogbeat 采集的 Windows 安全日志进行只读排查，定位账户锁定、登录失败等问题
author: OpsCore AIOps Agent
trigger: 用户要求排查 Windows 账户（工号/用户名）的登录、锁定、失败事件
scope: read_only
---

# Windows 安全日志排查专家 (Winlogbeat ES 排查)

## 重要：数据存储结构说明
- **索引命名模式**：`{人名}_windows_prod_syslog_YYYY.MM`
- **字段映射**：只有 5 个顶层字段（`@timestamp`, `message`, `tags`, `type`, `@version`），所有嵌套数据均存储在 `message` JSON 字符串中
- **message.keyword 被忽略**：因为 message 超过 32KB，无法用精确字段过滤

## API 路径选择（关键）

### ❌ 不要用：/api/console/proxy
- 此路径对超大 message 字段无法精确过滤
- 任何 match_phrase/term 查询都会变成全文子串匹配，返回大量噪声

### ✅ 正确路径：POST /internal/search/es
- Header：`kbn-xsrf: true`, `content-type: application/json`
- Body 格式：
```json
{
  "params": {
    "index": "zhaohui_windows_prod_syslog_2026.05",
    "body": {
      "query": {
        "bool": {
          "must": [
            {"query_string": {"query": "工号 AND (4625 OR 4771 OR 4740)", "analyze_wildcard": true}}
          ]
        }
      },
      "size": 20,
      "sort": [{"@timestamp": {"order": "desc"}}]
    }
  }
}
```

## 排查步骤（按优先级）

### Step 1: 先查索引列表和字段映射
```
GET /api/index_management/indices?from=0&size=50
GET /api/index_patterns/_fields_for_wildcard?pattern=zhaohui_windows_prod_syslog_2026.05
```

### Step 2: 组合查询——工号 + Event ID（必须！）
**一定要同时搜工号和 Event ID！** 不要只搜工号。

查询语法模板：
```
{工号} AND (4625 OR 4771 OR 4740)
```

### Step 3: 根据 Event ID 和 Status 判断问题类型

| 查询条件 | 含义 | 说明 |
|:--------:|:----|:----|
| `4625` + `0xC0000234` | 🔴 账户已锁定 | 已触达锁定阈值 |
| `4740` | 🔴 账户被锁定事件 | 记录谁触发了锁定 |
| `4771` + `0x12` | 🟡 **账户被禁用/吊销** | KDC_ERR_CLIENT_REVOKED，AD账号被手动禁用 |
| `4771` + `0x18` | 🟡 **密码错误** | KDC_ERR_PREAUTH_FAILED，Kerberos密码错误 |
| `4771` + PreAuthType=2 | 🟡 有预认证尝试 | 说明客户端确实发了密码，但密码不对 |
| `4771` + PreAuthType=0 | 🟡 无预认证 | 可能是账户禁用导致的自动失败 |
| `4625` + `0xC000006D` | 🟡 密码错误 | 用户名或密码错误 |
| `4624` | 🟢 登录成功 | 正常登录 |
| `4634` | ⚪ 注销 | 正常注销 |

### Step 4: 提取关键字段
从 message JSON 中提取：
- `winlog.event_id` - 事件ID
- `winlog.event_data.TargetUserName` - 目标账户（工号）
- `winlog.event_data.IpAddress` - 源IP地址
- `winlog.event_data.WorkstationName` - 工作站名
- `winlog.event_data.Status` - 状态码（十六进制）
- `winlog.computer_name` - 域控名

### Step 5: 交叉比对IP来源
当同一工号出现大量 4771 事件时：
1. **汇总所有来源IP**，区分高频和低频
2. 高频IP可能是恶意扫描或服务配置错误
3. 低频IP可能是正常业务尝试
4. 注意 `::ffff:` 前缀的IPv6映射地址等同于普通IPv4

### Step 6: 区分"锁定"和"禁用"
这是一个常见的混淆点：
- **0xC0000234** = 锁定（密码多次错误后AD自动锁定）
- **0x12** = 禁用（管理员手动在AD中禁用了账号）
- 如果是0x12，**不是锁定问题**，需要先联系AD管理员恢复账号

### Step 7: 可信运维来源过滤
- `192.168.111.45` 为 OpsCore 可信运维来源
- 来自该 IP 的登录应降级为正常运维访问，不列入异常

## 常见陷阱
1. ❌ 只搜工号不搜 Event ID → 返回海量噪声
2. ❌ 用 /api/console/proxy → 嵌套字段不生效
3. ❌ 忘了加 `analyze_wildcard: true` → 通配符不生效
4. ❌ 直接搜工号数字 → 被 ES 分词打散，匹配大量无关文档
5. ❌ **把 4771+0x12 误判为锁定** → 实际上是账号被禁用，不是锁定
6. ❌ **只看一条日志就下结论** → 应汇总所有IP和Status，看整体模式
7. ✅ 正确做法：`"工号 AND (4625 OR 4771)"` + **同时看Status值**

## 只读边界
- 所有操作均为只读查询
- 禁止写入、修改、删除任何 ES 数据
- 禁止使用 SSH 或直接登录 ES 节点
