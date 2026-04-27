"""WinRM execution adapter for Windows assets."""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger(__name__)


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
                encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
                result = session.run_cmd("powershell", ["-NoProfile", "-EncodedCommand", encoded])

            stdout = (result.std_out or b"").decode("utf-8", errors="replace").strip()
            stderr = (result.std_err or b"").decode("utf-8", errors="replace").strip()
            return {
                "success": result.status_code == 0,
                "exit_status": result.status_code,
                "output": stdout if stdout else stderr,
                "has_error": bool(stderr and result.status_code != 0),
            }
        except Exception as e:
            logger.error("WinRM command failed: %s", e)
            return {"success": False, "error": str(e)}


winrm_executor = WinRMExecutor()
