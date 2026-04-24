import os
import re
import yaml
import json
import asyncio
import subprocess
import logging
import time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SkillDispatcher:
    """
    【新版核心】：基于 Markdown 驱动的 Skill 动态扫描器。
    它会自动扫描配置目录下的 SKILL.md，提取名称和说明并将其转化为可供大模型感知的上下文本。
    """

    def __init__(self):
        self.skills_registry = {}
        self.pending_approvals = {}
        self._last_refresh_time = 0
        self._refresh_interval = 30  # 30 秒缓存，避免每次调用都全量扫描文件系统
        self.skill_directories = [
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "skills"
            ),  # 项目自带技能
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
            ),  # 你的专属私有技能目录
        ]
        # 外部插件市场目录（只看，不用，可点击复制入库）
        self.market_directories = [
            os.path.expanduser(r"~/.gemini/skills"),
            r"D:\AI\.claude\skills",
        ]
        self.refresh_skills()

    def refresh_skills(self, force: bool = False):
        """扫描目录并解析所有 SKILL.md，带时间戳缓存"""
        now = time.time()
        if (
            not force
            and (now - self._last_refresh_time) < self._refresh_interval
            and self.skills_registry
        ):
            return  # 缓存尚未过期，跳过全量扫描

        self.skills_registry.clear()

        for base_dir in self.skill_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")

                if os.path.isdir(folder_path) and os.path.exists(skill_md_path):
                    try:
                        self._parse_skill_md(skill_md_path, folder_path)
                    except Exception as e:
                        logger.error(f"解析 {skill_md_path} 失败: {e}")

        self._last_refresh_time = time.time()

    def _parse_skill_md(self, md_path: str, folder_path: str):
        """解析带有 YAML frontmatter 的 Markdown 文件"""
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 判断该技能来自哪个技能大本营
        if r".gemini" in folder_path:
            source_type = "Gemini Global 官方技能库"
        elif r".claude" in folder_path:
            source_type = "Claude 自定义技能库"
        elif "my_custom_skills" in folder_path:
            source_type = "OpsCore 私有技能"
        else:
            source_type = "OpsCore 内置技能"

        # 简单提取 --- 和 --- 之间的 yaml，以及下方的 markdown 主体
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()

                skill_id = frontmatter.get("name", os.path.basename(folder_path))

                code_blocks = re.findall(r"```", body)
                tool_count = max(len(code_blocks) // 2, 1)

                self.skills_registry[skill_id] = {
                    "id": skill_id,
                    "name": skill_id.replace("-", " ").title(),
                    "description": frontmatter.get("description", "未提供描述"),
                    "instructions": body,  # 这将喂给大模型
                    "source_path": folder_path,
                    "source_type": source_type,  # 标记该技能来源
                    "tool_count": tool_count,
                }

    def get_all_registered_skills(self) -> List[Dict[str, Any]]:
        """给前端提供本地已安装技能的摘要信息"""
        self.refresh_skills()
        return self._format_skills_for_ui(self.skills_registry.values())

    def get_market_skills(self) -> List[Dict[str, Any]]:
        """扫描外部插件市场，但不入库，仅供前端展示和复制"""
        market_skills = []
        for base_dir in self.market_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")

                if os.path.isdir(folder_path) and os.path.exists(skill_md_path):
                    # 如果该文件夹名已经在本地有了，就不在市场里展示为可下载（避免重复）
                    if skill_folder in self.skills_registry:
                        continue

                    try:
                        with open(skill_md_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                frontmatter = yaml.safe_load(parts[1])
                                body = parts[2].strip()

                                if r".gemini" in folder_path:
                                    source_type = "Gemini Global 官方技能库"
                                elif r".claude" in folder_path:
                                    source_type = "Claude 自定义技能库"
                                else:
                                    source_type = "外部未知技能"

                                market_skills.append(
                                    {
                                        "id": frontmatter.get("name", skill_folder),
                                        "name": frontmatter.get("name", skill_folder)
                                        .replace("-", " ")
                                        .title(),
                                        "description": frontmatter.get(
                                            "description", "未提供描述"
                                        ),
                                        "instructions": body,
                                        "source_path": folder_path,
                                        "source_type": source_type,
                                        "tool_count": max(
                                            len(re.findall(r"```", body)) // 2, 1
                                        ),
                                        "is_market": True,  # 标记为市场技能
                                    }
                                )
                    except Exception as e:
                        logger.error(f"解析市场卡带 {skill_md_path} 失败: {e}")

        return self._format_skills_for_ui(market_skills)

    def _format_skills_for_ui(self, skills_list) -> List[Dict[str, Any]]:
        """通用UI格式化"""
        result = []
        for v in skills_list:
            extracted_tools = []
            for line in v["instructions"].split("\n"):
                line = line.strip()
                if line.startswith("- **") or line.startswith("### "):
                    clean_line = (
                        line.replace("- **", "")
                        .replace("**:", "")
                        .replace("###", "")
                        .strip()
                    )
                    if len(clean_line) > 2 and len(clean_line) < 30:
                        extracted_tools.append(clean_line)

            if not extracted_tools:
                extracted_tools = ["基于 Markdown 的自定义指令"]

            result.append(
                {
                    "id": v["id"],
                    "name": v["name"],
                    "description": v["description"],
                    "tool_count": v["tool_count"],
                    "tools": list(set(extracted_tools))[:6],
                    "source_path": v["source_path"],
                    "source_type": v["source_type"],
                    "is_market": v.get("is_market", False),
                }
            )

        return result

    def get_skill_instructions(self, active_skill_ids: List[str]) -> str:
        """把用户勾选的所有技能的说明书（Markdown）拼接到一起，作为系统提示词给 AI 看"""
        instructions = ""
        for s_id in active_skill_ids:
            if s_id in self.skills_registry:
                skill = self.skills_registry[s_id]
                source_path = skill.get("source_path", "")
                instructions += f"\n\n<!-- 激活技能: {skill['name']} -->\n"
                instructions += "<ACTIVATED_SKILL>\n"
                instructions += (
                    f"<SKILL_ABSOLUTE_PATH>{source_path}</SKILL_ABSOLUTE_PATH>\n"
                )
                instructions += f"【重要指令】：此技能存放于物理路径 `{source_path}`。当你需要调用此技能内的 python 脚本时，请务必使用绝对路径，或者在使用 `local_execute_script` 工具时将 `cwd` 参数严格设置为该绝对路径，切勿自行猜测。\n"
                instructions += (
                    f"<INSTRUCTIONS>\n{skill['instructions']}\n</INSTRUCTIONS>\n"
                )
                instructions += "</ACTIVATED_SKILL>\n"
        return instructions

    def get_available_tools(
        self, current_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        不论用户勾选了什么技能，底层我们统一只给 AI 暴露两种终极物理工具：
        1. 连远程机器执行命令 (原有)
        2. 在宿主机（本地）执行 Python/Shell 脚本 (新！用于跑 Gemini CLI 里自带的那些外部工具)
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "local_execute_script",
                    "description": "在运维平台宿主机上执行本地命令或脚本。例如根据 SKILL 指示执行 `python scripts/xxx.py`。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要运行的本地命令",
                            },
                            "cwd": {
                                "type": "string",
                                "description": "工作目录（可选），如果不填则在默认目录运行",
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_notification",
                    "description": "当完成重要的故障排查、系统分析或执行了高危修改后，调用此工具向团队汇报结果。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "enum": ["auto", "wechat", "dingtalk", "email"],
                                "description": "要发送的渠道。填 'auto' 则自动选择系统已开启的默认渠道。",
                            },
                            "title": {
                                "type": "string",
                                "description": "消息标题（如：数据库告警排查结果、系统巡检报告）",
                            },
                            "content": {
                                "type": "string",
                                "description": "详细汇报内容，支持 Markdown 格式。请对你的排查过程和结论进行精炼总结。",
                            },
                        },
                        "required": ["channel", "title", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_active_sessions",
                    "description": "【总控特权】列出当前平台已连接的所有活跃资产会话（Session），获取它们的 session_id、IP、备注名和读写权限。在需要跨系统操作前必须先调用此工具获取目标的 session_id。",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "evolve_skill",
                    "description": "【自我进化】当你被用户要求更新、修改或创建一个技能卡带时，使用此工具直接修改物理硬盘上的技能文件。支持创建/覆盖 SKILL.md 或 python 脚本文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_id": {
                                "type": "string",
                                "description": "技能包名称的文件夹名（如 my-linux-skill），它将被创建在 my_custom_skills 目录下。",
                            },
                            "file_name": {
                                "type": "string",
                                "description": "要修改的文件名。通常是 SKILL.md 或 附加的 python 脚本（如 script.py）。",
                            },
                            "content": {
                                "type": "string",
                                "description": "文件的完整新内容。请注意，如果是 SKILL.md，必须包含 YAML frontmatter (即 --- name: ... ---)。",
                            },
                        },
                        "required": ["skill_id", "file_name", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "dispatch_sub_agents",
                    "description": "【批量协同】作为全局指挥官，一次性向多个会话/子Agent下发任务。执行时会并发调度，但最大并发限制为10以保护系统。返回所有任务的执行报告集合。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "target_session_id": {
                                            "type": "string",
                                            "description": "目标资产/专家的 session_id",
                                        },
                                        "task_description": {
                                            "type": "string",
                                            "description": "详细具体的任务指令",
                                        },
                                    },
                                    "required": [
                                        "target_session_id",
                                        "task_description",
                                    ],
                                },
                                "description": "要分发的子任务列表",
                            }
                        },
                        "required": ["tasks"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "检索企业内部运维知识库。当被问及账号、密码、IP地址、资产信息、或者遇到未知报错、需要参考SOP手册时，必须第一时间调用此工具去本地知识库搜索答案。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要检索的问题或关键词，例如 '数据库的密码是多少' 或 'Nginx 502 排查 SOP'",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "【联网检索】当本地知识库没有答案时，调用此工具去互联网搜索实时资料、官方文档或开源社区方案。使用 DuckDuckGo 引擎。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "要搜索的内容关键词，尽量精炼，例如 'k8s pod terminating status reason'",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

        target_scope = current_context.get("target_scope", "asset")

        if target_scope == "asset":
            # Asset scope gets direct linux and db execution
            tools.extend(
                [
                    {
                        "type": "function",
                        "function": {
                            "name": "linux_execute_command",
                            "description": "在连接的远程目标服务器上执行诊断命令。",
                            "parameters": {
                                "type": "object",
                                "properties": {"command": {"type": "string"}},
                                "required": ["command"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "db_execute_query",
                            "description": "通过原生驱动直连查询数据库（支持 mysql, oracle, postgresql）。比 SSH 命令更安全、结构化。Oracle 无需 jdbc。不依赖当前机器。请把 SQL 拼好发给我。",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "db_type": {
                                        "type": "string",
                                        "enum": ["mysql", "oracle", "postgresql"],
                                        "description": "数据库类型",
                                    },
                                    "host": {
                                        "type": "string",
                                        "description": "数据库主机 IP 或域名",
                                    },
                                    "port": {
                                        "type": "integer",
                                        "description": "数据库端口（如 MySQL 3306, Oracle 1521, PG 5432）",
                                    },
                                    "user": {
                                        "type": "string",
                                        "description": "登录用户名",
                                    },
                                    "password": {
                                        "type": "string",
                                        "description": "登录密码",
                                    },
                                    "database": {
                                        "type": "string",
                                        "description": "数据库名称（Oracle 传 SID 或 Service Name）",
                                    },
                                    "sql": {
                                        "type": "string",
                                        "description": "要执行的 SQL 查询语句",
                                    },
                                },
                                "required": [
                                    "db_type",
                                    "host",
                                    "port",
                                    "user",
                                    "password",
                                    "database",
                                    "sql",
                                ],
                            },
                        },
                    },
                ]
            )
        elif target_scope in ("group", "tag"):
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "execute_on_scope",
                        "description": "在当前标签/组内的所有目标资产上批量执行相同的 bash 命令。底层会并发拉起执行，并将相同的输出结果进行聚合（Scale到1000+机器不会撑爆上下文）。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "scope_target": {
                                    "type": "string",
                                    "description": "要执行的范围。如果你想在整个业务组的所有机器上执行，请传入 'ALL'。如果你只想测试部分机器，可传入逗号分隔的IP地址或主机名列表。",
                                },
                                "command": {
                                    "type": "string",
                                    "description": "要在所有目标上并发执行的 Bash 脚本或命令。",
                                },
                            },
                            "required": ["scope_target", "command"],
                        },
                    },
                }
            )
        elif target_scope == "global":
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": "search_assets_by_tag",
                        "description": "【全局检索】根据Tag标签搜索通讯录中的资产列表。例如要寻找“MES”相关机器，传入['MES']，返回所有匹配的IP和凭证ID。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "要搜索的业务或技术标签，例如 ['db', 'prod']",
                                }
                            },
                            "required": ["tags"],
                        },
                    },
                }
            )

        return tools

    async def route_and_execute(
        self, tool_call_name: str, args: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """执行大模型的意图"""
        if tool_call_name == "linux_execute_command":
            from connections.ssh_manager import ssh_manager

            session_id = context.get("session_id")
            if not session_id:
                return '{"error": "没有找到激活的远程会话"}'

            # 【这里保留之前的拦截逻辑代码，略简化】
            allow_mod = context.get("allow_modifications", False)
            # 增强版的只读模式拦截：使用正则词边界匹配，减少对 grep/cat 等只读命令的误杀
            if not allow_mod:
                cmd_str = args.get("command", "")
                # 危险写操作命令（必须在词边界处匹配，避免 "grep rm" 被误拦截）
                write_patterns = [
                    r"\brm\b",
                    r"\bmkdir\b",
                    r"\bmv\b",
                    r"\bcp\b",
                    r"\bvi\b",
                    r"\bvim\b",
                    r"\bnano\b",
                    r"\bchmod\b",
                    r"\bchown\b",
                    r"\bdd\b",
                    r"\bsystemctl\s+(start|stop|restart|enable|disable)\b",
                    r"\byum\s+(install|remove|erase)\b",
                    r"\bapt(-get)?\s+(install|remove|purge)\b",
                    r"\brpm\s+-[eUi]\b",
                    r"\bmkfs\b",
                    r"\bfdisk\b",
                    r"\bparted\b",
                    r">",  # 重定向写入
                ]
                if any(re.search(p, cmd_str) for p in write_patterns):
                    return '{"status": "BLOCKED", "reason": "只读安全模式，已拦截潜在的修改动作"}'

            result = await asyncio.to_thread(
                ssh_manager.execute_command, session_id, args.get("command")
            )
            return json.dumps(result)

        elif tool_call_name == "local_execute_script":
            # 这是为了兼容之前的 Gemini Skills，让它能在当前电脑上跑写的 python 脚本
            cmd = args.get("command")
            cwd = args.get("cwd") or os.getcwd()

            # 【轻量级安全防御】
            allow_mod = context.get("allow_modifications", False)
            if not allow_mod:
                write_patterns = [
                    r"\brm\b",
                    r"\bmkdir\b",
                    r"\bmv\b",
                    r"\bcp\b",
                    r"\bvi\b",
                    r"\bvim\b",
                    r"\bnano\b",
                    r"\bchmod\b",
                    r"\bchown\b",
                    r"\bdd\b",
                    r"\bsystemctl\s+(start|stop|restart|enable|disable)\b",
                    r"\byum\s+(install|remove|erase)\b",
                    r"\bapt(-get)?\s+(install|remove|purge)\b",
                    r"\brpm\s+-[eUi]\b",
                    r"\bmkfs\b",
                    r"\bfdisk\b",
                    r"\bparted\b",
                    r">",  # 重定向写入
                    # Windows
                    r"\bdel\b",
                    r"\bformat\b",
                    r"\brmdir\b",
                ]
                if any(re.search(p, cmd) for p in write_patterns):
                    return '{"status": "BLOCKED", "reason": "只读安全模式，已拦截潜在的修改动作"}'

            # 防止 AI 幻觉写出直接格式化硬盘或关闭操作系统的恶意指令。
            # 覆盖 Windows + Linux 双平台危险命令
            dangerous_commands = [
                # Windows
                "del /f /s /q",
                "format ",
                "shutdown ",
                "rmdir /s",
                "taskkill /f /im svchost",
                # Linux
                "rm -rf /",
                "mkfs.",
                "dd if=",
                ":(){ :|:& };:",
                "> /dev/sd",
                "shutdown -h",
                "halt",
                "poweroff",
                "init 0",
            ]
            if any(danger in cmd.lower() for danger in dangerous_commands):
                logger.warning(f"🚨 [Security] 拦截了 AI 试图执行的高危本地指令: {cmd}")
                return json.dumps(
                    {
                        "status": "BLOCKED",
                        "error": "指令触发了宿主机高危防御策略，已被系统拦截。请检查你的脚本逻辑。",
                    }
                )

            try:

                def run_script():
                    logger.info(f"Executing Local Script: {cmd} in {cwd}")
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"

                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        cwd=cwd,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )

                    try:
                        out_bytes, _ = process.communicate(timeout=60)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        out_bytes, _ = process.communicate()
                        return json.dumps(
                            {
                                "status": "ERROR",
                                "error": "脚本执行超时 (超过 60 秒)，已被系统强行中断。请检查是否有死循环或网络阻塞。",
                            }
                        )

                    try:
                        out = out_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        out = out_bytes.decode("gbk", errors="replace")

                    output_limit = 1024 * 1024
                    if len(out) > output_limit:
                        out = (
                            out[:output_limit]
                            + "\n...[警告：输出内容超大，已被安全截断至 1MB 以内]"
                        )

                    return json.dumps(
                        {
                            "status": "SUCCESS" if process.returncode == 0 else "ERROR",
                            "output": out,
                        }
                    )

                return await asyncio.to_thread(run_script)
            except Exception as e:
                return json.dumps({"error": str(e)})

        elif tool_call_name == "send_notification":
            channel = args.get("channel", "auto")
            title = args.get("title")
            content = args.get("content")

            def do_notify():
                logger.info(f"AI 发起了群组通知 -> 渠道: {channel}, 标题: {title}")
                from core.notifier import send_notification

                result = send_notification(channel, title, content)
                return json.dumps(result)

            return await asyncio.to_thread(do_notify)

        elif tool_call_name == "db_execute_query":
            from connections.db_manager import db_executor

            db_type = args.get("db_type")
            host = args.get("host")
            port = args.get("port")
            user = args.get("user")
            password = args.get("password")
            database = args.get("database")
            sql = args.get("sql")

            allow_mod = context.get("allow_modifications", False)
            if not allow_mod and sql:
                # 危险的数据库写操作和DDL命令
                sql_write_patterns = [
                    r"\binsert\b",
                    r"\bupdate\b",
                    r"\bdelete\b",
                    r"\bdrop\b",
                    r"\balter\b",
                    r"\btruncate\b",
                    r"\breplace\b",
                    r"\bgrant\b",
                    r"\brevoke\b",
                    r"\bcommit\b",
                    r"\brollback\b",
                ]
                if any(re.search(p, sql, re.IGNORECASE) for p in sql_write_patterns):
                    return '{"status": "BLOCKED", "reason": "只读安全模式，已拦截潜在的数据库修改动作"}'

            logger.info(
                f"AI 调用原生数据库驱动 [{db_type.upper()}] 查询: {host}:{port}/{database} -> SQL: {sql}"
            )

            return await asyncio.to_thread(
                db_executor.execute_query,
                db_type,
                host,
                port,
                user,
                password,
                database,
                sql,
            )

        elif tool_call_name == "list_active_sessions":
            from connections.ssh_manager import ssh_manager

            sessions_info = []
            for sid, sdata in list(ssh_manager.active_sessions.items()):
                info = sdata["info"]
                sessions_info.append(
                    {
                        "session_id": sid,
                        "host": info.get("host"),
                        "remark": info.get("remark", ""),
                        "profile": info.get("agent_profile", ""),
                        "allow_modifications": info.get("allow_modifications", False),
                    }
                )
            logger.info(
                f"总控 Agent 请求了活跃资产列表，当前在线: {len(sessions_info)} 台"
            )
            return json.dumps({"active_sessions": sessions_info}, ensure_ascii=False)

        elif tool_call_name == "dispatch_sub_agents":
            from core.agent import dispatch_group_tasks

            tasks = args.get("tasks", [])
            parent_allow_mod = context.get("allow_modifications", False)

            results = await dispatch_group_tasks(tasks, parent_allow_mod)
            return json.dumps(
                {"status": "BATCH_COMPLETE", "results": results}, ensure_ascii=False
            )

        elif tool_call_name == "execute_on_scope":
            scope_target = args.get("scope_target", "ALL")
            command = args.get("command", "")
            parent_allow_mod = context.get("allow_modifications", False)

            if not parent_allow_mod:
                write_patterns = [
                    r"\brm\b",
                    r"\bmkdir\b",
                    r"\bmv\b",
                    r"\bcp\b",
                    r"\bvi\b",
                    r"\bvim\b",
                    r"\bnano\b",
                    r"\bchmod\b",
                    r"\bchown\b",
                    r"\bdd\b",
                    r"\bsystemctl\s+(start|stop|restart|enable|disable)\b",
                    r"\byum\s+(install|remove|erase)\b",
                    r"\bapt(-get)?\s+(install|remove|purge)\b",
                    r"\brpm\s+-[eUi]\b",
                    r"\bmkfs\b",
                    r"\bfdisk\b",
                    r"\bparted\b",
                    r">",
                ]
                if any(re.search(p, command) for p in write_patterns):
                    return '{"status": "BLOCKED", "reason": "只读安全模式，已拦截潜在的修改动作"}'

            from connections.ssh_manager import ssh_manager

            target_tag = context.get("scope_value", "")
            if (
                isinstance(target_tag, str)
                and target_tag.startswith("[")
                and target_tag.endswith("]")
            ):
                target_tag = target_tag[1:-1]

            tasks = []
            for sid, sdata in ssh_manager.active_sessions.items():
                info = sdata["info"]

                if target_tag and target_tag not in info.get("tags", []):
                    continue

                host = info.get("host")
                remark = info.get("remark", "")

                if (
                    scope_target == "ALL"
                    or (host and host in scope_target)
                    or (remark and remark in scope_target)
                ):
                    tasks.append((sid, host or remark))

            if not tasks:
                return json.dumps(
                    {
                        "error": f"找不到匹配的在线资产会话 (Tag: {target_tag}, Target: {scope_target})。"
                    }
                )

            sem = asyncio.Semaphore(50)

            async def _run_single(t_sid, t_host):
                async with sem:
                    res = await asyncio.to_thread(
                        ssh_manager.execute_command, t_sid, command
                    )
                    return t_host, res

            completed = await asyncio.gather(
                *(_run_single(sid, host) for sid, host in tasks)
            )

            results_dict = {}
            for h, res in completed:
                if res.get("success"):
                    out = str(res.get("output", ""))
                else:
                    out = str(res.get("error", "ERROR"))

                if not out.strip():
                    out = "[空输出]"

                if out not in results_dict:
                    results_dict[out] = []
                results_dict[out].append(h)

            aggregated_res = {}
            for out, hosts in results_dict.items():
                summary_key = f"{len(hosts)} hosts returned this output"
                display_hosts = hosts[:5] + (["..."] if len(hosts) > 5 else [])
                aggregated_res[summary_key] = {"hosts": display_hosts, "output": out}

            return json.dumps(
                {
                    "status": "BATCH_COMPLETE",
                    "total_hosts": len(tasks),
                    "results": aggregated_res,
                },
                ensure_ascii=False,
            )

        elif tool_call_name == "evolve_skill":
            skill_id = args.get("skill_id", "")
            file_name = args.get("file_name", "")
            content = args.get("content", "")

            # 限制只能修改自己的 my_custom_skills 目录
            target_base = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
            )
            os.makedirs(target_base, exist_ok=True)

            # 安全校验，防止目录穿越
            if ".." in skill_id or "/" in skill_id or "\\" in skill_id:
                return json.dumps({"error": "非法路径，禁止包含特殊字符或目录穿越符"})

            safe_file_name = os.path.basename(file_name)
            dest_folder = os.path.join(target_base, skill_id)
            os.makedirs(dest_folder, exist_ok=True)

            file_path = os.path.join(dest_folder, safe_file_name)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"AI 成功自我进化：更新了文件 -> {file_path}")

                # 通知 Dispatcher 重新加载
                self.refresh_skills()
                return json.dumps(
                    {
                        "status": "SUCCESS",
                        "message": f"技能卡带文件 {file_name} 已经成功更新并热重载！现在您可以告诉用户它已经生效了。",
                    }
                )
            except Exception as e:
                return json.dumps({"error": f"写入文件失败: {str(e)}"})

        elif tool_call_name == "search_knowledge_base":
            from core.rag import kb_manager
            from core.llm_factory import get_client_for_model

            client, _ = get_client_for_model("gemini-2.5-flash")

            query = args.get("query")
            try:
                result = await asyncio.wait_for(
                    kb_manager.search(query, client), timeout=60.0
                )
                return json.dumps({"status": "SUCCESS", "results": result})
            except asyncio.TimeoutError:
                return json.dumps({"error": "知识库检索超时被强制截断。"})
            except Exception as e:
                return json.dumps({"error": f"知识库检索异常: {str(e)}"})

        elif tool_call_name == "web_search":
            query = args.get("query")
            try:

                def do_search():
                    from duckduckgo_search import DDGS

                    logger.info(f"AI 发起了外网检索: {query}")
                    with DDGS() as ddgs:
                        return [r for r in ddgs.text(query, max_results=5)]

                results = await asyncio.to_thread(do_search)
                return json.dumps(
                    {"status": "SUCCESS", "results": results}, ensure_ascii=False
                )
            except Exception as e:
                return json.dumps({"error": f"外网检索异常: {str(e)}"})

        elif tool_call_name == "search_assets_by_tag":
            tags_to_search = args.get("tags", [])
            from core.memory import memory_db

            try:
                all_assets = await asyncio.to_thread(memory_db.get_all_assets)

                # Filter assets by tags
                matched_assets = []
                for asset in all_assets:
                    asset_tags = asset.get("tags", [])
                    # Verify if the asset has all the requested tags
                    if all(tag in asset_tags for tag in tags_to_search):
                        # Filter out sensitive fields
                        safe_asset = {
                            "id": asset.get("id"),
                            "host": asset.get("host"),
                            "port": asset.get("port"),
                            "username": asset.get("username"),
                            "asset_type": asset.get("asset_type"),
                            "remark": asset.get("remark"),
                            "tags": asset.get("tags"),
                        }
                        matched_assets.append(safe_asset)

                logger.info(
                    f"AI 发起了全局资产检索 tags={tags_to_search}, 匹配 {len(matched_assets)} 台"
                )
                return json.dumps(
                    {
                        "status": "SUCCESS",
                        "matched_count": len(matched_assets),
                        "assets": matched_assets,
                    },
                    ensure_ascii=False,
                )
            except Exception as e:
                logger.error(f"search_assets_by_tag 发生异常: {e}")
                return json.dumps({"error": f"全局检索异常: {str(e)}"})

        return '{"error": "Unknown tool"}'


# 全局单例
dispatcher = SkillDispatcher()
