from typing import Dict, Any, List
from skills.base import BaseSkillProvider
import json

class LinuxSkillProvider(BaseSkillProvider):
    """专门为 Linux 服务器设计的运维技能组"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "linux_execute_command",
                    "description": "在当前的 Linux SSH 会话中执行 Shell 命令。可以进行系统诊断、资源查看，以及安全的文件/目录操作（如 mkdir, touch, echo 等）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的 bash/shell 命令。例如：ps aux | grep java 或 mkdir -p /data/test"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "linux_read_file",
                    "description": "读取 Linux 服务器上的文件内容（如日志）。会自动使用 head/tail/cat。禁止读取过大的文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "文件绝对路径。例如：/var/log/syslog"
                            },
                            "lines": {
                                "type": "integer",
                                "description": "需要读取的行数。默认 50。"
                            }
                        },
                        "required": ["filepath"]
                    }
                }
            }
        ]
    
    def execute(self, tool_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> str:
        # 这里会拿到核心层传入的上下文，里面包含关键的 session_id
        session_id = context.get("session_id")
        allow_modifications = context.get("allow_modifications", False)
        
        if not session_id:
            return json.dumps({"error": "缺少激活的 Session ID"})

        # 从 core 服务导入我们刚才写的执行模块
        from connections.ssh_manager import ssh_manager
        
        if tool_name == "linux_execute_command":
            cmd = args.get("command")
            
            if not allow_modifications:
                # --- 【只读安全模式】物理拦截所有修改动作 ---
                # 为了防止误拦截 (比如 "grep form" 匹配到 "rm")，我们在前后加空格匹配或者精确匹配命令头
                cmd_parts = cmd.split()
                if cmd_parts:
                    base_cmd = cmd_parts[0]
                    write_keywords = ["mkdir", "touch", "rm", "mv", "cp", "chmod", "chown", "apt-get", "yum", "systemctl", "vi", "nano", "wget", "curl"]
                    # 修复：重定向到 /dev/null 这种查询命令是合法的。只有重定向到普通文件才算违规写入。
                    is_dangerous_redirect = ">" in cmd and "/dev/null" not in cmd and "&1" not in cmd
                    
                    if base_cmd in write_keywords or is_dangerous_redirect:
                        return json.dumps({
                            "status": "BLOCKED", 
                            "reason": "当前会话处于【只读安全模式】。检测到违规命令或文件覆写动作。如需执行，请先点击界面顶部的安全徽章进行提权。"
                        })
            else:
                # --- 【读写特权模式】仅拦截同归于尽的操作 ---
                dangerous_keywords = ["rm -rf", "reboot -f", "mkfs", "dd if="]
                if any(keyword in cmd for keyword in dangerous_keywords):
                    return json.dumps({
                        "status": "BLOCKED", 
                        "reason": "AI 企图执行极度危险的破坏性操作，被底层内置拦截器强制阻挡。"
                    })
                
            res = ssh_manager.execute_command(session_id, cmd)
            return json.dumps(res)
            
        elif tool_name == "linux_read_file":
            filepath = args.get("filepath")
            lines = args.get("lines", 50)
            
            # 安全限制：为了防止大模型把整个 2GB 的日志读回爆内存，强制加 tail 限制
            safe_cmd = f"tail -n {lines} {filepath}"
            res = ssh_manager.execute_command(session_id, safe_cmd)
            return json.dumps(res)
            
        return json.dumps({"error": f"未知的 Linux 技能: {tool_name}"})
