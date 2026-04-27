import os
import re
import yaml
import json
import asyncio
import subprocess
import logging
import time
import shlex
from typing import Dict, Any, List

from core.asset_protocols import API_PROTOCOLS, NETWORK_CLI_ASSET_TYPES, SQL_PROTOCOLS, resolve_asset_identity
from core.safety_policy import (
    check_approval_needed as policy_check_approval_needed,
    check_hard_block,
    check_readonly_block,
)
from core.skill_lifecycle import validate_skill_candidate, validate_skill_frontmatter
from core.tool_registry import tool_registry

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

        new_registry = {}

        for base_dir in self.skill_directories:
            if not os.path.exists(base_dir):
                continue

            for skill_folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, skill_folder)
                skill_md_path = os.path.join(folder_path, "SKILL.md")

                if os.path.isdir(folder_path) and os.path.exists(skill_md_path):
                    try:
                        self._parse_skill_md(skill_md_path, folder_path, new_registry)
                    except Exception as e:
                        logger.error(f"解析 {skill_md_path} 失败: {e}")

        self.skills_registry = new_registry
        self._last_refresh_time = time.time()

    def _parse_skill_md(self, md_path: str, folder_path: str, registry: dict):
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

                registry[skill_id] = {
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

    def get_skill_instructions(
        self, active_skill_ids: List[str], allow_local_scripts: bool = True
    ) -> str:
        """把用户勾选的所有技能的说明书（Markdown）拼接到一起，作为系统提示词给 AI 看"""
        instructions = ""
        if active_skill_ids and not allow_local_scripts:
            instructions += (
                "\n\n【协议优先约束】：当前是真实资产的原生协议会话，已挂载 Skill 只能作为知识/SOP 参考；"
                "禁止执行 Skill 中的 python/bash/本地脚本示例，必须使用当前会话暴露的原生协议工具完成操作。\n"
            )
        for s_id in active_skill_ids:
            if s_id in self.skills_registry:
                skill = self.skills_registry[s_id]
                source_path = skill.get("source_path", "")
                instructions += f"\n\n<!-- 激活技能: {skill['name']} -->\n"
                instructions += "<ACTIVATED_SKILL>\n"
                if allow_local_scripts:
                    instructions += (
                        f"<SKILL_ABSOLUTE_PATH>{source_path}</SKILL_ABSOLUTE_PATH>\n"
                    )
                    instructions += f"【重要指令】：此技能存放于物理路径 `{source_path}`。当你需要调用此技能内的 python 脚本时，请务必使用绝对路径，或者在使用 `local_execute_script` 工具时将 `cwd` 参数严格设置为该绝对路径，切勿自行猜测。\n"
                else:
                    instructions += "【重要指令】：当前会话禁止执行此 Skill 内的本地脚本；其中脚本示例仅作知识参考。\n"
                instructions += (
                    f"<INSTRUCTIONS>\n{skill['instructions']}\n</INSTRUCTIONS>\n"
                )
                instructions += "</ACTIVATED_SKILL>\n"
        return instructions

    def get_active_skill_paths(self, active_skill_ids: List[str]) -> List[str]:
        self.refresh_skills()
        paths = []
        for s_id in active_skill_ids:
            skill = self.skills_registry.get(s_id)
            if skill and skill.get("source_path"):
                paths.append(os.path.realpath(skill["source_path"]))
        return paths

    def _custom_skills_base(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "my_custom_skills"
        )

    @staticmethod
    def _validate_skill_frontmatter(skill_id: str, content: str) -> tuple[bool, str]:
        return validate_skill_frontmatter(skill_id, content)

    @staticmethod
    def _atomic_write_text(file_path: str, content: str) -> None:
        tmp_path = os.path.join(
            os.path.dirname(file_path),
            f".{os.path.basename(file_path)}.{time.time_ns()}.tmp",
        )
        try:
            with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, file_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def _backup_existing_skill_file(file_path: str) -> str | None:
        if not os.path.exists(file_path):
            return None
        versions_dir = os.path.join(os.path.dirname(file_path), ".versions")
        os.makedirs(versions_dir, exist_ok=True)
        backup_name = f"{os.path.basename(file_path)}.{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}.bak"
        backup_path = os.path.join(versions_dir, backup_name)
        with open(file_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
            dst.flush()
            os.fsync(dst.fileno())
        return backup_path

    def _validate_local_execution(
        self, command: str, cwd: str, context: Dict[str, Any]
    ) -> tuple[bool, str]:
        if not command or not isinstance(command, str):
            return False, "本地执行命令不能为空"

        if re.search(r"(&&|\|\||[;&|`<>])", command):
            return False, "禁止在 local_execute_script 中使用 Shell 控制符或重定向"

        active_paths = context.get("active_skill_paths") or self.get_active_skill_paths(
            context.get("active_skills", [])
        )
        if not active_paths:
            return False, "local_execute_script 只能在已挂载 Skill 的目录内执行"

        real_cwd = os.path.realpath(cwd or os.getcwd())
        real_active_paths = [os.path.realpath(p) for p in active_paths]
        try:
            if not any(
                os.path.commonpath([real_cwd, p]) == p for p in real_active_paths
            ):
                return False, "local_execute_script 的 cwd 必须位于已挂载 Skill 目录内"
        except ValueError:
            return False, "local_execute_script 的 cwd 路径非法"

        try:
            parts = shlex.split(command, posix=os.name != "nt")
        except ValueError as e:
            return False, f"命令解析失败: {e}"

        if not parts:
            return False, "本地执行命令不能为空"

        executable = os.path.basename(parts[0]).lower()
        allowed_executables = {
            "python",
            "python.exe",
            "python3",
            "python3.exe",
            "py",
            "py.exe",
            "powershell",
            "powershell.exe",
            "pwsh",
            "pwsh.exe",
        }
        if executable not in allowed_executables:
            return False, "local_execute_script 只允许调用解释器运行已挂载 Skill 内的脚本"

        return True, ""

    def check_approval_needed(self, tool_call_name: str, args: dict, context: dict) -> tuple[bool, str]:
        """【安全层】检查当前大模型执行的指令是否需要人类审批。"""
        from connections.ssh_manager import ssh_manager
        
        session_id = context.get("session_id")
        if session_id and session_id in ssh_manager.active_sessions:
            if ssh_manager.active_sessions[session_id]["info"].get("auto_approve_all", False):
                return False, ""
        return policy_check_approval_needed(tool_call_name, args, context)

    def get_available_tools(

        self, current_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Return protocol-aware tool schemas from the central registry."""
        return tool_registry.get_openai_tools(current_context)

    async def route_and_execute(
        self, tool_call_name: str, args: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """执行大模型的意图"""
        hard_blocked, hard_reason = check_hard_block(tool_call_name, args)
        if hard_blocked:
            logger.warning(
                "Hard blocked tool call %s for session %s: %s",
                tool_call_name,
                context.get("session_id"),
                hard_reason,
            )
            return json.dumps(
                {"status": "BLOCKED", "reason": hard_reason}, ensure_ascii=False
            )

        if tool_call_name in {
            "linux_execute_command",
            "container_execute_command",
            "middleware_execute_command",
            "storage_execute_command",
        }:
            from connections.ssh_manager import ssh_manager

            identity = resolve_asset_identity(
                context.get("asset_type"),
                context.get("protocol"),
                context.get("extra_args") or {},
                context.get("host"),
                context.get("port"),
                context.get("remark"),
            )
            if identity["protocol"] != "ssh":
                return json.dumps(
                    {"status": "ERROR", "error": f"当前资产协议是 {identity['protocol']}，不能使用 {tool_call_name}；请使用对应的原生协议工具。"},
                    ensure_ascii=False,
                )
            if identity["asset_type"] in NETWORK_CLI_ASSET_TYPES:
                return json.dumps(
                    {
                        "status": "ERROR",
                        "error": "当前资产是网络设备，不能使用 Linux 命令工具；请使用 network_cli_execute_command。",
                    },
                    ensure_ascii=False,
                )

            session_id = context.get("session_id")
            if not session_id:
                return '{"error": "没有找到激活的远程会话"}'

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            result = await asyncio.to_thread(
                ssh_manager.execute_command, session_id, args.get("command")
            )
            return json.dumps(result)

        elif tool_call_name == "winrm_execute_command":
            from connections.winrm_manager import winrm_executor

            extra_args = context.get("extra_args") or {}
            command = args.get("command")
            if args.get("password") or args.get("username"):
                logger.warning("winrm_execute_command ignored model-supplied credentials and used managed session credentials.")

            if not all([context.get("host"), context.get("port"), context.get("username"), context.get("password") is not None, command]):
                return json.dumps(
                    {
                        "status": "ERROR",
                        "error": "WinRM 会话凭据不完整，请检查资产中心配置的 host/port/user/password。",
                    },
                    ensure_ascii=False,
                )

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            result = await asyncio.to_thread(
                winrm_executor.execute_command,
                host=context.get("host"),
                port=context.get("port"),
                username=context.get("username"),
                password=context.get("password"),
                command=command,
                extra_args=extra_args,
            )
            return json.dumps(result, ensure_ascii=False)

        elif tool_call_name == "network_cli_execute_command":
            from connections.ssh_manager import ssh_manager

            session_id = context.get("session_id")
            if not session_id:
                return '{"error": "没有找到激活的网络设备会话"}'

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            result = await asyncio.to_thread(
                ssh_manager.execute_network_cli_command,
                session_id,
                args.get("command"),
            )
            return json.dumps(result, ensure_ascii=False)

        elif tool_call_name == "local_execute_script":
            # 这是为了兼容之前的 Gemini Skills，让它能在当前电脑上跑写的 python 脚本
            cmd = args.get("command")
            cwd = args.get("cwd") or os.getcwd()

            is_valid, reason = self._validate_local_execution(cmd, cwd, context)
            if not is_valid:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            try:

                def run_script():
                    logger.info(f"Executing Local Script: {cmd} in {cwd}")
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"

                    process = subprocess.Popen(
                        shlex.split(cmd, posix=os.name != "nt"),
                        shell=False,
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

                    output_limit = 2 * 1024 * 1024 # 2MB limit (适配目前主流 100万~200万 Token 的大模型上下文)
                    if len(out) > output_limit:
                        out = out[:output_limit] + "\\n...[警告：输出内容超大，已被截断至 2MB 以内]"

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

            extra_args = context.get("extra_args") or {}
            db_type = (
                args.get("db_type")
                or extra_args.get("db_type")
                or extra_args.get("login_protocol")
                or context.get("protocol")
                or context.get("asset_type")
                or "mysql"
            )
            db_type = str(db_type).lower()
            if db_type not in SQL_PROTOCOLS:
                return json.dumps(
                    {
                        "status": "ERROR",
                        "error": f"当前数据源协议是 {db_type}，不能使用 db_execute_query；请使用对应的数据源工具。",
                    },
                    ensure_ascii=False,
                )
            host = context.get("host") or args.get("host")
            port = context.get("port") or args.get("port")
            user = context.get("username") or args.get("user")
            password = context.get("password")
            database = (
                extra_args.get("SID")
                or extra_args.get("service_name")
                or extra_args.get("database")
                or extra_args.get("db_name")
                or args.get("database")
                or ""
            )
            sql = args.get("sql")

            if args.get("password"):
                logger.warning("db_execute_query ignored model-supplied password and used managed session credentials.")
            if args.get("database") and database != args.get("database"):
                logger.warning("db_execute_query ignored model-supplied database and used managed session database.")

            if not all([db_type, host, port, user, password is not None, sql]):
                return json.dumps(
                    {
                        "status": "ERROR",
                        "error": "数据库会话凭据不完整，请检查资产中心配置的 host/port/user/password/database。",
                    },
                    ensure_ascii=False,
                )

            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

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

        elif tool_call_name == "redis_execute_command":
            from connections.datastore_manager import redis_executor

            command = args.get("command", "")
            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            result = await asyncio.to_thread(
                redis_executor.execute_command,
                host=context.get("host"),
                port=context.get("port"),
                username=context.get("username") or "",
                password=context.get("password"),
                command=command,
                extra_args=context.get("extra_args") or {},
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_call_name == "mongodb_find":
            from connections.datastore_manager import mongo_executor

            extra_args = context.get("extra_args") or {}
            database = args.get("database") or extra_args.get("database") or extra_args.get("db_name") or "admin"
            result = await asyncio.to_thread(
                mongo_executor.find,
                host=context.get("host"),
                port=context.get("port"),
                username=context.get("username") or "",
                password=context.get("password"),
                database=database,
                collection=args.get("collection"),
                filter_doc=args.get("filter") or {},
                projection=args.get("projection"),
                limit=args.get("limit") or 100,
                extra_args=extra_args,
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_call_name in {
            "http_api_request",
            "k8s_api_request",
            "monitoring_api_query",
            "virtualization_api_request",
            "storage_api_request",
        }:
            from connections.http_api_manager import http_api_executor

            if tool_call_name == "virtualization_api_request" and context.get("protocol") == "winrm":
                return await self.route_and_execute(
                    "winrm_execute_command",
                    {"command": args.get("command") or args.get("path") or "Get-VM | Select-Object -First 20 | ConvertTo-Json -Compress"},
                    context,
                )
            if tool_call_name == "storage_api_request" and context.get("protocol") == "snmp":
                return await self.route_and_execute(
                    "snmp_get",
                    {"oid": args.get("oid") or "1.3.6.1.2.1.1.1.0"},
                    context,
                )

            method = str(args.get("method") or "GET").upper()
            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)

            result = await asyncio.to_thread(
                http_api_executor.request,
                asset_type=context.get("asset_type") or "",
                host=context.get("host"),
                port=context.get("port"),
                username=context.get("username") or "",
                password=context.get("password"),
                extra_args=context.get("extra_args") or {},
                method=method,
                path=args.get("path") or "/",
                headers=args.get("headers") or {},
                body=args.get("body"),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_call_name == "snmp_get":
            from connections.snmp_manager import snmp_executor

            extra_args = dict(context.get("extra_args") or {})
            if extra_args.get("v3_auth_user") and not extra_args.get("v3_username"):
                extra_args["v3_username"] = extra_args.get("v3_auth_user")
            elif context.get("username") and not any(
                extra_args.get(key)
                for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
            ):
                extra_args.setdefault("v3_username", context.get("username"))
            result = await asyncio.to_thread(
                snmp_executor.get,
                host=context.get("host"),
                port=context.get("port") or 161,
                oid=args.get("oid"),
                extra_args=extra_args,
            )
            return json.dumps(result, ensure_ascii=False, default=str)

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
                        "asset_type": info.get("asset_type"),
                        "protocol": info.get("protocol"),
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
            blocked, reason = check_readonly_block(tool_call_name, args, context)
            if blocked:
                return json.dumps({"status": "BLOCKED", "reason": reason}, ensure_ascii=False)
            if not str(command).strip():
                return json.dumps({"status": "ERROR", "error": "范围执行命令不能为空。"}, ensure_ascii=False)

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
                identity = resolve_asset_identity(
                    info.get("asset_type"),
                    info.get("protocol"),
                    info.get("extra_args", {}),
                    info.get("host"),
                    info.get("port"),
                    info.get("remark"),
                )
                if identity["protocol"] != "ssh":
                    continue

                if target_tag and target_tag not in info.get("tags", []):
                    continue

                host = info.get("host")
                remark = info.get("remark", "")

                if (
                    scope_target == "ALL"
                    or (host and host in scope_target)
                    or (remark and remark in scope_target)
                ):
                    tasks.append((sid, host or remark, identity["asset_type"]))

            if not tasks:
                return json.dumps(
                    {
                        "error": f"找不到匹配的在线资产会话 (Tag: {target_tag}, Target: {scope_target})。"
                    }
                )

            sem = asyncio.Semaphore(50)

            async def _run_single(t_sid, t_host, t_asset_type):
                async with sem:
                    actual_tool = (
                        "network_cli_execute_command"
                        if t_asset_type == "switch"
                        else "linux_execute_command"
                    )
                    hard_blocked, hard_reason = check_hard_block(actual_tool, args)
                    if hard_blocked:
                        return t_host, {"success": False, "error": hard_reason}
                    session_info = ssh_manager.active_sessions.get(t_sid, {}).get("info", {})
                    readonly_blocked, readonly_reason = check_readonly_block(
                        actual_tool, args, {**context, **session_info}
                    )
                    if readonly_blocked:
                        return t_host, {"success": False, "error": readonly_reason}

                    if actual_tool == "network_cli_execute_command":
                        res = await asyncio.to_thread(
                            ssh_manager.execute_network_cli_command, t_sid, command
                        )
                    else:
                        res = await asyncio.to_thread(
                            ssh_manager.execute_command, t_sid, command
                        )
                    return t_host, res

            completed = await asyncio.gather(
                *(_run_single(sid, host, asset_type) for sid, host, asset_type in tasks)
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
            unique_outputs_count = 0
            
            # Sort by number of hosts (descending) so we keep the most common outputs first
            sorted_results = sorted(results_dict.items(), key=lambda x: len(x[1]), reverse=True)
            
            for out, hosts in sorted_results:
                unique_outputs_count += 1
                if unique_outputs_count > 20:
                    aggregated_res["..."] = {"note": f"剩余 {len(sorted_results) - 20} 种不同的输出结果因篇幅限制被折叠。为了保护上下文，建议您优化命令输出(例如只返回关键的 error code 或做 wc -l 统计)。"}
                    break
                    
                summary_key = f"{len(hosts)} hosts returned this output"
                display_hosts = hosts[:5] + (["..."] if len(hosts) > 5 else [])
                aggregated_res[summary_key] = {"hosts": display_hosts, "output": out}

            return json.dumps(
                {
                    "status": "BATCH_COMPLETE",
                    "total_hosts": len(tasks),
                    "unique_outputs": len(results_dict),
                    "results": aggregated_res,
                },
                ensure_ascii=False,
            )

        elif tool_call_name == "evolve_skill":
            skill_id = args.get("skill_id", "")
            file_name = args.get("file_name", "")
            content = args.get("content", "")

            skill_id = str(skill_id or "").strip()
            file_name = str(file_name or "").strip()
            content = str(content or "")

            # 限制只能修改自己的 my_custom_skills 目录
            target_base = self._custom_skills_base()
            os.makedirs(target_base, exist_ok=True)

            validation = validate_skill_candidate(skill_id, file_name, content)
            if not validation["valid"]:
                detail = "；".join(issue["message"] for issue in validation["issues"])
                return json.dumps({"error": detail}, ensure_ascii=False)

            dest_folder = os.path.join(target_base, skill_id)
            os.makedirs(dest_folder, exist_ok=True)

            safe_file_name = validation["file_name"]
            file_path = os.path.join(dest_folder, safe_file_name)
            try:
                backup_path = self._backup_existing_skill_file(file_path)
                self._atomic_write_text(file_path, content)
                logger.info(f"AI 成功自我进化：更新了文件 -> {file_path}")

                # 通知 Dispatcher 重新加载
                self.refresh_skills()
                return json.dumps(
                    {
                        "status": "SUCCESS",
                        "message": f"技能卡带文件 {file_name} 已经成功更新并热重载！现在您可以告诉用户它已经生效了。",
                        "skill_id": skill_id,
                        "file_name": safe_file_name,
                        "file_path": file_path,
                        "backup_path": backup_path,
                    }
                )
            except Exception as e:
                return json.dumps({"error": f"写入文件失败: {str(e)}"})

        elif tool_call_name == "search_knowledge_base":
            from core.rag import kb_manager
            from core.llm_factory import get_embedding_client_and_model

            client, embedding_model = get_embedding_client_and_model()

            query = args.get("query")
            try:
                result = await asyncio.wait_for(
                    kb_manager.search(query, client, embedding_model), timeout=60.0
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
                            "protocol": asset.get("protocol"),
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
