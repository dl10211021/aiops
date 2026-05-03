"""Local script execution boundary for mounted skills."""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
from collections.abc import Sequence

LOCAL_SCRIPT_TIMEOUT_SECONDS = 60
LOCAL_SCRIPT_OUTPUT_LIMIT = 2 * 1024 * 1024
ALLOWED_LOCAL_SCRIPT_EXECUTABLES = {
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


def validate_local_execution(
    command: str,
    cwd: str,
    active_paths: Sequence[str] | None,
) -> tuple[bool, str]:
    if not command or not isinstance(command, str):
        return False, "本地执行命令不能为空"

    if re.search(r"(&&|\|\||[;&|`<>])", command):
        return False, "禁止在 local_execute_script 中使用 Shell 控制符或重定向"

    if not active_paths:
        return False, "local_execute_script 只能在已挂载 Skill 的目录内执行"

    real_cwd = os.path.realpath(cwd or os.getcwd())
    real_active_paths = [os.path.realpath(path) for path in active_paths]
    try:
        if not any(os.path.commonpath([real_cwd, path]) == path for path in real_active_paths):
            return False, "local_execute_script 的 cwd 必须位于已挂载 Skill 目录内"
    except ValueError:
        return False, "local_execute_script 的 cwd 路径非法"

    try:
        parts = shlex.split(command, posix=os.name != "nt")
    except ValueError as exc:
        return False, f"命令解析失败: {exc}"

    if not parts:
        return False, "本地执行命令不能为空"

    executable = os.path.basename(parts[0]).lower()
    if executable not in ALLOWED_LOCAL_SCRIPT_EXECUTABLES:
        return False, "local_execute_script 只允许调用解释器运行已挂载 Skill 内的脚本"

    return True, ""


def execute_local_script(
    command: str,
    cwd: str,
    logger: logging.Logger | None = None,
) -> str:
    if logger:
        logger.info("Executing Local Script: %s in %s", command, cwd)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    process = subprocess.Popen(
        shlex.split(command, posix=os.name != "nt"),
        shell=False,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        out_bytes, _ = process.communicate(timeout=LOCAL_SCRIPT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return json.dumps(
            {
                "status": "ERROR",
                "error": "脚本执行超时 (超过 60 秒)，已被系统强行中断。请检查是否有死循环或网络阻塞。",
            }
        )

    try:
        output = out_bytes.decode("utf-8")
    except UnicodeDecodeError:
        output = out_bytes.decode("gbk", errors="replace")

    if len(output) > LOCAL_SCRIPT_OUTPUT_LIMIT:
        output = output[:LOCAL_SCRIPT_OUTPUT_LIMIT] + "\n...[警告：输出内容超大，已被截断至 2MB 以内]"

    return json.dumps(
        {
            "status": "SUCCESS" if process.returncode == 0 else "ERROR",
            "output": output,
        }
    )
