from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Callable

MASKED_VALUE = "********"

NOTIFICATION_ENV_KEYS = (
    "WECHAT_ENABLED",
    "WECHAT_WEBHOOK_URL",
    "DINGTALK_ENABLED",
    "DINGTALK_WEBHOOK_URL",
    "EMAIL_ENABLED",
    "ALERT_EMAIL_ADDRESS",
    "SMTP_SERVER",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
)


def env_or_existing(value: str, env_key: str, env: Mapping[str, str] | None = None) -> str:
    if value == MASKED_VALUE:
        source = os.environ if env is None else env
        return source.get(env_key, "")
    return value


def _notification_channel_status(
    *,
    channel: str,
    label: str,
    enabled: bool,
    configured: bool,
    required_fields: list[str],
) -> dict[str, object]:
    if not enabled:
        status = "disabled"
        message = "通道未启用。"
    elif configured:
        status = "ready"
        message = "通道已启用且关键配置完整，可发送测试消息。"
    else:
        status = "missing_config"
        message = "通道已启用，但关键配置不完整。"
    return {
        "channel": channel,
        "label": label,
        "enabled": enabled,
        "configured": configured,
        "ready": enabled and configured,
        "status": status,
        "message": message,
        "required_fields": required_fields,
    }


def build_notification_channel_statuses(source: Mapping[str, str]) -> list[dict[str, object]]:
    wechat_enabled = source.get("WECHAT_ENABLED", "1") == "1"
    dingtalk_enabled = source.get("DINGTALK_ENABLED", "1") == "1"
    email_enabled = source.get("EMAIL_ENABLED", "1") == "1"
    return [
        _notification_channel_status(
            channel="wechat",
            label="企业微信",
            enabled=wechat_enabled,
            configured=bool(source.get("WECHAT_WEBHOOK_URL")),
            required_fields=["WECHAT_WEBHOOK_URL"],
        ),
        _notification_channel_status(
            channel="dingtalk",
            label="钉钉",
            enabled=dingtalk_enabled,
            configured=bool(source.get("DINGTALK_WEBHOOK_URL")),
            required_fields=["DINGTALK_WEBHOOK_URL"],
        ),
        _notification_channel_status(
            channel="email",
            label="邮件",
            enabled=email_enabled,
            configured=bool(
                source.get("ALERT_EMAIL_ADDRESS")
                and source.get("SMTP_SERVER")
                and source.get("SMTP_USER")
                and source.get("SMTP_PASS")
            ),
            required_fields=[
                "ALERT_EMAIL_ADDRESS",
                "SMTP_SERVER",
                "SMTP_USER",
                "SMTP_PASS",
            ],
        ),
    ]


def build_notification_config(env: Mapping[str, str] | None = None) -> dict[str, object]:
    source = os.environ if env is None else env
    return {
        "wechat_enabled": source.get("WECHAT_ENABLED", "1") == "1",
        "wechat_webhook": MASKED_VALUE if source.get("WECHAT_WEBHOOK_URL") else "",
        "dingtalk_enabled": source.get("DINGTALK_ENABLED", "1") == "1",
        "dingtalk_webhook": MASKED_VALUE if source.get("DINGTALK_WEBHOOK_URL") else "",
        "email_enabled": source.get("EMAIL_ENABLED", "1") == "1",
        "email_address": source.get("ALERT_EMAIL_ADDRESS", ""),
        "smtp_server": source.get("SMTP_SERVER", ""),
        "smtp_port": int(source.get("SMTP_PORT", "465")),
        "smtp_user": source.get("SMTP_USER", ""),
        "smtp_pass": MASKED_VALUE if source.get("SMTP_PASS") else "",
        "channels": build_notification_channel_statuses(source),
    }


def build_notification_env_values(
    config: Mapping[str, object],
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    source = os.environ if env is None else env
    values = {
        "WECHAT_ENABLED": "1" if config["wechat_enabled"] else "0",
        "WECHAT_WEBHOOK_URL": env_or_existing(
            str(config["wechat_webhook"]),
            "WECHAT_WEBHOOK_URL",
            source,
        ),
        "DINGTALK_ENABLED": "1" if config["dingtalk_enabled"] else "0",
        "DINGTALK_WEBHOOK_URL": env_or_existing(
            str(config["dingtalk_webhook"]),
            "DINGTALK_WEBHOOK_URL",
            source,
        ),
        "EMAIL_ENABLED": "1" if config["email_enabled"] else "0",
        "ALERT_EMAIL_ADDRESS": str(config["email_address"]),
        "SMTP_SERVER": str(config["smtp_server"]),
        "SMTP_PORT": str(config["smtp_port"]),
        "SMTP_USER": str(config["smtp_user"]),
        "SMTP_PASS": env_or_existing(str(config["smtp_pass"]), "SMTP_PASS", source),
    }
    return {key: values[key] for key in NOTIFICATION_ENV_KEYS}


def save_notification_config(
    config: Mapping[str, object],
    *,
    env: dict[str, str] | None = None,
    persist: Callable[[dict[str, str]], None] | None = None,
) -> dict[str, str]:
    target_env = os.environ if env is None else env
    values = build_notification_env_values(config, target_env)
    target_env.update(values)
    if persist:
        persist(values)
    return values
