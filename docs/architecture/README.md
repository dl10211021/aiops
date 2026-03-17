# OpsCore 系统架构与开发指南

## 1. 系统概览

OpsCore 是一个基于 FastAPI 与大语言模型 (LLM) 深度整合的 AIOps 平台后端。它允许用户（或前端界面）通过自然语言与远程服务器（或本地环境）进行交互，平台会自动将意图转换为可执行的指令（如 SSH 命令、数据库查询、脚本运行等），并在执行前通过系统卡点机制保证安全性。

### 核心特性
- **Agent 驱动**: 基于 Gemini / OpenAI 协议的模型调度。
- **动态技能库 (Skills)**: 通过 Markdown 文件动态加载技能，实现模型能力的无缝扩展。
- **长短期记忆 (Memory & RAG)**: 结合 SQLite 与 LanceDB，实现会话上下文管理和历史操作向量检索。
- **安全拦截**: 执行破坏性命令前的权限审计与人工确认机制。

---

## 2. 目录结构与核心模块

```text
.
├── main.py                # 应用程序入口，FastAPI 实例与生命周期管理
├── api/
│   └── routes.py          # HTTP 接口定义（包含 Chat, 资产管理, 配置中心等）
├── core/                  # AIOps 核心引擎
│   ├── agent.py           # LLM API 客户端封装，支持 Streaming 与 Headless 模式
│   ├── dispatcher.py      # 【核心】技能调度器，负责解析 SKILL.md、挂载工具函数 (tools)
│   ├── memory.py          # 历史会话管理 (SQLite) 与 长时记忆 (LanceDB 向量化)
│   ├── rag.py             # 检索增强生成模块（目前结合知识库）
│   ├── cron_manager.py    # 定时任务管理模块
│   └── heartbeat.py       # 心跳检测机制
├── connections/           # 底层交互层
│   ├── ssh_manager.py     # SSH 客户端池，负责建立连接和执行 Shell 命令
│   └── db_manager.py      # 数据库连接池（如 MySQL, Oracle 等关系型数据库分析）
├── skills/                # 官方内置技能库 (以目录和 SKILL.md 形式存在)
├── my_custom_skills/      # 用户自定义私有技能库
├── static_react/          # 前端 React 构建产物挂载点
└── opscore.db             # 主控数据库 (SQLite)
```

---

## 3. 核心流转过程 (请求 -> 响应)

以用户发送一条 "帮我看看服务器的 CPU 负载" 为例：

1. **接口接收**: `api/routes.py` 中的 `/chat` 或对应 WebSocket 接收到消息。
2. **上下文组装**: `core/memory.py` 获取此 `session_id` 的短期历史记忆和 RAG 检索到的长期记忆。
3. **工具绑定**: `core/dispatcher.py` 扫描挂载在当前 session 上的 Skills，并转换成供 LLM 调用的 functions (tools)。
4. **LLM 规划**: `core/agent.py` 带着上下文和工具描述向大模型发请求。模型决定调用 `execute_command` 工具，并生成查询负载的命令（如 `top -b -n 1`）。
5. **权限与执行**: `core/dispatcher.py` 拦截工具调用请求。如果是敏感操作，可能触发 pending approval 流程返回给前端确认。确认无误后，通过 `connections/ssh_manager.py` 在目标主机上执行命令。
6. **结果反馈**: 执行结果写回 Memory，Agent 生成最终自然语言回复，通过 `api/routes.py` stream 给前端。

---

## 4. 如何进行二次开发？

### 场景一：我想新增一个控制台接口 / 前端想加个按钮
- **修改位置**: `api/routes.py`
- **操作指南**: 使用 `@router.post(...)` 或 `@router.get(...)` 编写你的逻辑。如果需要持久化数据，请在 `core/memory.py` 或新建的 DB module 中编写 SQL 操作（当前项目重度使用原生 SQLite 和简单封装）。
- **注意**: 若修改配置类接口，记得同步更新单例内存中的状态。

### 场景二：我想增加一种模型能调用的 "动作" (例如：发邮件)
- **修改位置**: 
  1. 新建一个技能目录：`my_custom_skills/send-email/SKILL.md`。
  2. 在 `core/dispatcher.py` 中的 `route_and_execute` 方法以及 `get_available_tools` 中硬编码/注册相关的 python 回调函数（目前很多底层方法是写死在 dispatcher 里的，如 `do_notify`）。
- **最佳实践**: 仔细观察 `dispatcher.py` 是如何把 python 函数包装成 json schema 提供给大模型的。

### 场景三：我想修改连接服务器的方式 (例如支持 Paramiko 的特定密钥认证)
- **修改位置**: `connections/ssh_manager.py`
- **操作指南**: 找到 `SSHConnectionManager.connect` 方法。当前它支持密码和 `key_filename`。若需增加代理、堡垒机跳板等逻辑，在此处扩展 Paramiko client 的设定即可。

### 场景四：调试为什么 Agent “乱说话” 或 “找错工具”
- **修改位置**: `core/agent.py` 与 `core/dispatcher.py`
- **排查指南**: 
  - 查看 `logging` 输出的 `function_call` 名称和参数。
  - 检查对应 Skill 的 Markdown 描述是否足够清晰，导致模型误判。
  - 检查 `memory.py` 中 `retrieve_ltm` 检索到的长期记忆是否污染了当前上下文。

## 5. 启动与调试
- 本地调试直接运行 `python main.py`，默认监听在 `http://localhost:9000`。
- API 交互文档可见于 `http://localhost:9000/docs`。
- `.env` 文件用于环境变量配置。