from __future__ import annotations

from typing import Any


CONNECTION_ERROR_MESSAGES = {
    "credential_invalid": "密码错误：用户名或密码不正确。请检查账号、密码、密钥或认证方式。",
    "connection_failed": "连接失败：无法连接到目标服务。请检查主机地址、端口、防火墙、服务是否启动以及网络连通性。",
    "internal_error": "内部错误：连接处理过程中发生异常，请查看后端日志。",
}


def classify_connection_error(
    raw_error: Any,
    protocol: str = "",
    context: str = "",
) -> dict[str, str]:
    """Normalize connection failures into user-facing categories."""
    raw = str(raw_error or "").strip()
    text = f"{protocol} {context} {raw}".lower()

    credential_markers = (
        "authentication failed",
        "auth failed",
        "bad authentication",
        "bad credentials",
        "invalid credentials",
        "invalid password",
        "invalid username/password",
        "password authentication failed",
        "permission denied (publickey,password",
        "permission denied, please try again",
        "access denied for user",
        "login failed",
        "ora-01017",
        "1045",
        "noauth authentication required",
        "auth required",
        "authenticationerror",
        "unauthorized",
        "401 unauthorized",
        "认证失败",
        "用户名或密码错误",
        "密码错误",
    )
    connection_markers = (
        "timed out",
        "timeout",
        "connection refused",
        "connection reset",
        "connection aborted",
        "no route to host",
        "network is unreachable",
        "host is unreachable",
        "could not connect",
        "cannot connect",
        "unable to connect",
        "failed to establish a new connection",
        "getaddrinfo failed",
        "name or service not known",
        "temporary failure in name resolution",
        "tcp connect failed",
        "max retries exceeded",
        "no valid connections",
        "actively refused",
        "winrm_connection",
        "server not found",
        "service unavailable",
        "目标计算机积极拒绝",
        "连接超时",
        "连接被拒绝",
        "无法连接",
    )

    if any(marker in text for marker in credential_markers):
        code = "credential_invalid"
        category = "credential"
    elif any(marker in text for marker in connection_markers):
        code = "connection_failed"
        category = "connection"
    else:
        code = "internal_error"
        category = "internal"

    return {
        "code": code,
        "category": category,
        "message": CONNECTION_ERROR_MESSAGES[code],
        "raw_error": raw,
        "protocol": str(protocol or ""),
    }


def connection_error_http_status(error: dict[str, Any]) -> int:
    category = error.get("category")
    if category == "credential":
        return 401
    if category == "connection":
        return 502
    return 500
