"""WinRM execution adapter for Windows assets."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _decode_stream(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value or "").strip()


def _classify_winrm_error(message: str) -> dict:
    text = str(message or "").strip()
    lower = text.lower()
    if not text:
        return {
            "error_type": "winrm_error",
            "message": "WinRM 执行失败，但远端未返回详细错误。",
            "hint": "请检查目标会话是否仍在线，并在会话中重试一个简单命令，如 whoami。",
        }

    if any(token in lower for token in ("parsererror", "parseexception", "missing closing", "unexpected token", "term is not recognized")):
        return {
            "error_type": "powershell_syntax",
            "message": "PowerShell 脚本语法或命令名称解析失败。",
            "hint": "请检查引号、括号、脚本块、哈希表写法，以及命令是否在目标 Windows 主机上存在。",
        }
    if any(token in lower for token in ("access is denied", "unauthorizedaccessexception", "permissiondenied", "拒绝访问", "访问被拒绝")):
        return {
            "error_type": "permission_denied",
            "message": "当前 WinRM 账号缺少执行该读取或管理动作的 Windows 权限。",
            "hint": "请确认账号属于本机 Administrators、Event Log Readers 或对应资源的读取组；读取 Security 日志尤其需要事件日志权限。",
        }
    if any(token in lower for token in ("running scripts is disabled", "executionpolicy", "cannot be loaded because running scripts")):
        return {
            "error_type": "powershell_execution_policy",
            "message": "目标 Windows 主机的 PowerShell 执行策略限制了脚本运行。",
            "hint": "优先改成单行只读命令；如确需脚本执行，请由管理员调整目标主机 PowerShell 执行策略。",
        }
    if any(token in lower for token in ("401", "unauthorized", "forbidden", "ntlm", "kerberos", "authentication")):
        return {
            "error_type": "winrm_authentication",
            "message": "WinRM 认证或授权失败。",
            "hint": "请检查资产中心账号密码、域账号格式、transport 设置，以及目标 WinRM 认证方式。",
        }
    if any(token in lower for token in ("timed out", "timeout", "connection refused", "failed to establish", "name or service not known", "no route to host")):
        return {
            "error_type": "winrm_connection",
            "message": "无法稳定连接到目标 WinRM 服务。",
            "hint": "请检查 5985/5986 端口、防火墙、HTTPS/HTTP 配置、网络连通性和目标 WinRM 服务状态。",
        }

    return {
        "error_type": "winrm_command_failed",
        "message": "WinRM 命令执行失败。",
        "hint": "请查看原始错误，必要时先执行 whoami、hostname、Get-ComputerInfo 验证会话状态。",
    }


class WinRMExecutor:
    def execute_command(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str | None,
        command: str,
        extra_args: dict | None = None,
    ) -> dict:
        """Execute a PowerShell command via the managed Windows asset credentials."""
        extra_args = extra_args or {}
        if not all([host, port, username, password is not None, command]):
            return {
                "success": False,
                "error": "WinRM 会话凭据不完整，请检查资产中心 host/port/user/password。",
            }

        try:
            import winrm
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pywinrm 依赖，请先安装 requirements.txt 中的 pywinrm 后再连接 Windows 资产。",
            }

        use_ssl = bool(extra_args.get("use_ssl") or int(port) == 5986)
        scheme = "https" if use_ssl else "http"
        endpoint = str(extra_args.get("endpoint") or f"{scheme}://{host}:{int(port)}/wsman")
        transport = str(extra_args.get("transport") or "ntlm")

        try:
            session = winrm.Session(endpoint, auth=(username, password), transport=transport)
            shell = str(extra_args.get("shell") or "powershell").lower()
            if shell == "cmd":
                result = session.run_cmd(command)
            else:
                result = session.run_ps(command)

            stdout = _decode_stream(result.std_out)
            stderr = _decode_stream(result.std_err)
            success = result.status_code == 0
            output = stdout if stdout else stderr
            response = {
                "success": success,
                "exit_status": result.status_code,
                "output": output,
                "has_error": bool(stderr and result.status_code != 0),
            }
            if not success:
                classified = _classify_winrm_error(output)
                response.update(classified)
                response["error"] = classified["message"]
                response["raw_error"] = stderr or stdout
            if stdout and stderr:
                response["stderr"] = stderr
            return {
                **response,
            }
        except Exception as e:
            logger.error("WinRM command failed: %s", e)
            classified = _classify_winrm_error(str(e))
            return {
                "success": False,
                "error": classified["message"],
                "raw_error": str(e),
                **classified,
            }


winrm_executor = WinRMExecutor()
