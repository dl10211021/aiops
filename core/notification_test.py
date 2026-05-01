from __future__ import annotations

import datetime
import json
import os
import urllib.request
from collections.abc import Mapping
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class NotificationTestError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def build_notification_test_content(
    now: datetime.datetime | None = None,
) -> tuple[str, str]:
    current = now or datetime.datetime.now()
    title = "SkillOps 平台连通性测试"
    content = (
        "这是一条来自 SkillOps 平台的测试消息。如果您看到此消息，说明告警通道配置正常。\n\n"
        f"**发送时间**: {current.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return title, content


def build_notification_webhook_payload(channel: str, title: str, content: str) -> dict:
    if channel == "wechat":
        return {
            "msgtype": "markdown",
            "markdown": {"content": f"## {title}\n{content}"},
        }
    if channel == "dingtalk":
        return {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": f"## {title}\n{content}"},
        }
    raise NotificationTestError(422, "不支持的渠道类型")


def send_notification_channel_test(
    channel: str,
    env: Mapping[str, str] | None = None,
    now: datetime.datetime | None = None,
) -> str:
    source = os.environ if env is None else env
    title, content = build_notification_test_content(now)

    if channel == "wechat":
        webhook = source.get("WECHAT_WEBHOOK_URL", "")
        if not webhook:
            raise NotificationTestError(400, "请先配置企业微信 Webhook 地址")
        _post_webhook(webhook, build_notification_webhook_payload(channel, title, content))
        return "企业微信测试消息发送成功！请查看您的群组。"

    if channel == "dingtalk":
        webhook = source.get("DINGTALK_WEBHOOK_URL", "")
        if not webhook:
            raise NotificationTestError(400, "请先配置钉钉 Webhook 地址")
        _post_webhook(webhook, build_notification_webhook_payload(channel, title, content))
        return "钉钉测试消息发送成功！请查看您的群组。"

    if channel == "email":
        return _send_email_test(source, title, content)

    raise NotificationTestError(422, "不支持的渠道类型")


def _post_webhook(webhook: str, payload: dict) -> None:
    request = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(request, timeout=5)


def _send_email_test(source: Mapping[str, str], title: str, content: str) -> str:
    email_address = source.get("ALERT_EMAIL_ADDRESS", "")
    smtp_server = source.get("SMTP_SERVER", "")
    smtp_port = int(source.get("SMTP_PORT", 465) or 465)
    smtp_user = source.get("SMTP_USER", "")
    smtp_pass = source.get("SMTP_PASS", "")

    if not email_address:
        raise NotificationTestError(400, "请先配置接收人邮箱地址")
    if not smtp_server or not smtp_user or not smtp_pass:
        raise NotificationTestError(400, "发送失败：尚未配置完整的 SMTP 发件服务器参数。")

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = email_address
    msg["Subject"] = title
    msg.attach(MIMEText(content, "plain", "utf-8"))

    import smtplib

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, email_address, msg.as_string())
    server.quit()
    return f"测试邮件已成功发送至 {email_address}！"
