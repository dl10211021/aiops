from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from ipaddress import ip_address


class SessionWebhookError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def validate_webhook_url(url: str, allow_private_targets: bool = False) -> tuple[str, dict]:
    stripped = str(url or "").strip()
    parsed = urllib.parse.urlparse(stripped)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SessionWebhookError(422, "Webhook 地址必须是 http 或 https URL。")
    if parsed.username or parsed.password:
        raise SessionWebhookError(422, "Webhook 地址不能包含用户名或密码。")
    if parsed.fragment:
        raise SessionWebhookError(422, "Webhook 地址不能包含 URL fragment。")

    host = parsed.hostname or ""
    if not host:
        raise SessionWebhookError(422, "Webhook 地址缺少目标主机。")

    resolved_ips: list[str] = []
    try:
        for info in socket.getaddrinfo(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        ):
            ip = info[4][0]
            if ip not in resolved_ips:
                resolved_ips.append(ip)
    except socket.gaierror as exc:
        raise SessionWebhookError(422, f"Webhook 主机无法解析: {host}") from exc

    private_ips: list[str] = []
    for ip_text in resolved_ips:
        try:
            ip = ip_address(ip_text)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            private_ips.append(ip_text)
    if private_ips and not allow_private_targets:
        raise SessionWebhookError(
            422,
            f"Webhook 目标解析到内网或保留地址 {', '.join(private_ips[:3])}，请确认后勾选允许内网目标。",
        )

    return stripped, {
        "scheme": parsed.scheme,
        "host": host,
        "port": parsed.port or (443 if parsed.scheme == "https" else 80),
        "resolved_ips": resolved_ips[:5],
        "private_target": bool(private_ips),
    }


def build_session_webhook_payload(
    session_id: str,
    payload_type: str,
    channel: str,
    title: str,
    markdown: str,
    profile: dict | None,
) -> dict:
    if channel == "wechat":
        return {"msgtype": "markdown", "markdown": {"content": f"## {title}\n{markdown[:3600]}"}}
    if channel == "dingtalk":
        return {"msgtype": "markdown", "markdown": {"title": title, "text": f"## {title}\n{markdown[:3600]}"}}
    return {
        "type": "opscore.session_report",
        "session_id": session_id,
        "payload_type": payload_type,
        "title": title,
        "markdown": markdown,
        "profile": profile,
        "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def webhook_payload_preview(payload: dict) -> dict:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return {
        "bytes": len(text.encode("utf-8")),
        "preview": text[:2500],
        "truncated": len(text) > 2500,
    }


def post_webhook(url: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as resp:
            body = resp.read(2048).decode("utf-8", errors="replace")
            return resp.getcode(), body
    except urllib.error.HTTPError as exc:
        body = exc.read(2048).decode("utf-8", errors="replace")
        return exc.code, body
