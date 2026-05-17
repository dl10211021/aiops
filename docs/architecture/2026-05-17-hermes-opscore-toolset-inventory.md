# Hermes Toolset vs OpsCore Tool Registry 对照

日期：2026-05-17

## 1. 结论

本对照用于决定 OpsCore 后续工具补齐方向。结论很明确：

- Hermes 的强项是通用 Agent 工具面：浏览器、文件、终端、进程、Skill、Memory、Session Search、Cron、Delegation、Kanban、Gateway 通道。
- OpsCore 的强项是 AIOps 运维工具面：资产协议、数据库、SSH/WinRM/SNMP/Redis/MongoDB/Memcached、监控日志 API、K8s、虚拟化、存储、网络、安全、CI/CD、大数据、AI 平台、通知、审批和工具证据。
- OpsCore 不应该全量复制 Hermes 工具。应按 AIOps 价值分为：核心必补、受控接入、通道接入、暂不接入。
- 当前最缺的是 `session_search`、`delegate_task`、`cronjob`、`execute_code`、`process`、`patch/write_file/skill_manage` 的平台化接入和审批审计，而不是更多非运维工具。

## 2. 数据来源

- Hermes：`.research/hermes-agent/toolsets.py`
- OpsCore：`core/tool_registry.py`
- OpsCore 工具中心受控清单：`core/tool_center_service.py`

本轮只读取 Hermes 源码，不编辑 `.research/hermes-agent/`。

## 3. 数量概览

| 项目 | 数量 | 说明 |
| --- | ---: | --- |
| Hermes unique tools | 79 | 从所有 `TOOLSETS` 聚合去重 |
| OpsCore registered tools | 62 | 从 `tool_registry.all_tools()` 读取 |
| OpsCore controlled/not wired Hermes tools | 12 | 工具中心已列出但默认不暴露或未接入 |

## 4. Hermes 工具分层

### 4.1 AIOps 核心必须覆盖

| Hermes 工具 | OpsCore 状态 | 处理建议 |
| --- | --- | --- |
| `web_search` | 已有 `web_search`，同时受控清单里也存在同名 Hermes 工具 | 保留 OpsCore 知识检索包装，后续统一状态说明，避免工具中心看起来重复 |
| `web_extract` | 已有 `web_extractor` | 视为已适配，名称保持 OpsCore 语义 |
| `browser_navigate` | 已有 | 保留 |
| `browser_snapshot` | 已有 | 保留 |
| `browser_click` | 已有 | 保留 |
| `browser_type` | 已有 | 保留 |
| `browser_scroll` | 已有 | 保留 |
| `browser_back` | 已有 | 保留 |
| `browser_press` | 已有 | 保留 |
| `browser_get_images` | 已有 | 保留 |
| `browser_vision` | 已有 | 保留 |
| `browser_console` | 已有 | 保留 |
| `read_file` | 已有 | 保留，只允许受限路径和只读语义 |
| `search_files` | 已有 | 保留 |
| `todo` | 已有 | 保留，后续接入 AIOps Run stages |
| `vision_analyze` | 已有 | 保留，用于截图、报告、资产界面分析 |
| `skills_list` | 已有 | 保留 |
| `skill_view` | 已有 | 保留 |

### 4.2 AIOps 核心但仍需平台化接入

| Hermes 工具 | OpsCore 状态 | 缺口 |
| --- | --- | --- |
| `session_search` | 工具中心标记 `not_wired` | 需要接入会话历史、工具证据、审批、trace 的 FTS/CJK 检索 |
| `delegate_task` | 工具中心标记 `not_wired` | 需要映射到 OpsCore 全局/组/单会话多 Agent 分发，不直接复制 Hermes delegate |
| `cronjob` | 工具中心受控 | 需要和 OpsCore 巡检计划、AIOps Run、审批、通知结果统一 |
| `execute_code` | 工具中心受控 | 只能在 VIRTUAL/Skill 沙箱或明确审批环境运行 |
| `process` | 工具中心受控 | 需要进程清单、启动、停止、清理的审计和超时 |
| `patch` | 工具中心受控 | 仅用于受控 Skill/配置文件编辑，必须有 diff 和回滚 |
| `write_file` | 工具中心受控 | 默认不暴露给真实资产会话 |
| `skill_manage` | 工具中心受控 | 需要进入 Skill 候选、质量清单、发布审批、版本回滚 |
| `send_message` | 工具中心受控 | 应映射到通知中心，而不是普通模型外发 |
| `text_to_speech` | 工具中心受控 | 非核心，可用于报告播报，默认不暴露 |
| `memory` | 工具中心受控 | OpsCore 已拆成 `memory_list/read/write/edit/delete`，应继续保留拆分后的审计模型 |

### 4.3 Hermes 有但 OpsCore 暂不应作为核心

| Hermes 工具组 | 工具 | 决策 |
| --- | --- | --- |
| Computer Use | `computer_use` | 暂不作为默认运维路径；未来可作为高级受控桌面自动化 |
| Kanban | `kanban_show/list/complete/block/heartbeat/comment/create/link/unblock` | 不复制通用看板；吸收为 AIOps Run Board 的心跳、阻塞、完成、交接 |
| HomeAssistant | `ha_*` | 非 AIOps 主线，不接入核心 |
| Discord | `discord`, `discord_admin` | 作为通道中心候选，不进入核心工具 |
| Feishu 文档/Drive | `feishu_doc_read`, `feishu_drive_*` | 作为企业知识/通道能力候选，先不做核心 |
| Yuanbao | `yb_*` | 非当前企业运维主线，暂不接入 |
| Spotify | `spotify_*` | 不接入 |
| RL | `rl_*` | 不接入 |
| MOA | `mixture_of_agents` | 不直接接入；OpsCore 用自己的辅助模型审核和多 Agent 分发 |
| Video | `video_analyze` | 暂不接入，可作为后续截图/录屏分析扩展 |

## 5. OpsCore AIOps 原生工具优势

这些是 Hermes 没有、但 OpsCore 必须保留并强化的运维核心能力。

| 类别 | OpsCore 工具 |
| --- | --- |
| Linux/Windows/网络执行 | `linux_execute_command`, `winrm_execute_command`, `network_cli_execute_command` |
| 数据库 | `db_execute_query`, `mongodb_find`, `redis_execute_command`, `memcached_execute_command` |
| 批量和编排 | `execute_on_scope`, `dispatch_sub_agents`, `list_active_sessions`, `search_assets_by_tag` |
| 监控/日志/API | `monitoring_api_query`, `http_api_request`, `database_api_request` |
| 平台 API | `k8s_api_request`, `virtualization_api_request`, `container_api_request`, `storage_api_request`, `network_api_request` |
| 运维生态 API | `security_api_request`, `cicd_api_request`, `bigdata_api_request`, `middleware_api_request`, `discovery_api_request`, `ai_platform_api_request`, `oob_api_request`, `service_probe_request` |
| 中间件/存储执行 | `container_execute_command`, `middleware_execute_command`, `storage_execute_command` |
| 知识和通知 | `search_knowledge_base`, `web_research`, `web_extractor`, `send_notification`, `request_user_interaction` |
| Skill 研发 | `evolve_skill`, `local_execute_script` |

## 6. 状态分类建议

OpsCore 工具中心应统一使用以下状态，不要只用“可用/不可用”。

| 状态 | 含义 | 示例 |
| --- | --- | --- |
| `available` | 当前可被模型按策略调用 | `db_execute_query`, `linux_execute_command`, `web_search` |
| `controlled` | 平台已有元数据，但默认不暴露或必须审批 | `write_file`, `patch`, `execute_code`, `cronjob` |
| `not_wired` | 工具概念存在，但还没接入会话/审批/审计链路 | `session_search`, `delegate_task` |
| `not_applicable` | Hermes 有但不属于 OpsCore AIOps 主线 | `spotify_*`, `rl_*`, `ha_*` |
| `adapted` | Hermes 工具已用 OpsCore 名称适配 | `web_extract -> web_extractor`, `image_generate -> image_gen`, `memory -> memory_*` |

## 7. 下一步任务

优先级从高到低：

1. `session_search`：建立历史会话、工具证据、审批、trace 的检索 API 和模型工具。
2. `delegate_task`：映射到 OpsCore 全局/组/单会话多 Agent，继承权限上限。
3. `cronjob`：和巡检计划、AIOps Run、通知结果合并，不另起一套定时任务模型。
4. `process`：补后台进程审计、超时和清理。
5. `execute_code`：只允许在 VIRTUAL/Skill 沙箱或审批环境下运行。
6. `patch/write_file/skill_manage`：进入 Skill/Runbook 发布审批和回滚链。
7. 工具中心前端：增加“运维核心 / 通道 / 学习 / 受控危险 / 暂未接入 / 不适用”分组。

## 8. 不做

- 不把 Spotify、HomeAssistant、RL、Yuanbao、Discord 管理类工具放入 OpsCore 核心。
- 不让模型绕过 OpsCore 资产中心、凭证托管、审批、证据和审计直接调用 Hermes 原始工具。
- 不把 `send_message` 做成自由外发工具；必须接通知中心和发送记录。
- 不把 `delegate_task` 做成无边界子任务；必须继承全局/组/会话权限上限。
