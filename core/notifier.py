import os
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


def send_notification(channel: str, title: str, content: str) -> dict:
    """
    统一通知发送入口。支持 wechat / dingtalk / email / auto。
    返回 dict: {"status": "SUCCESS"/"ERROR", "message": "..."}
    """
    wechat_enabled = os.environ.get("WECHAT_ENABLED", "0") == "1"
    dingtalk_enabled = os.environ.get("DINGTALK_ENABLED", "0") == "1"
    email_enabled = os.environ.get("EMAIL_ENABLED", "0") == "1"

    wechat_webhook = os.environ.get("WECHAT_WEBHOOK_URL", "")
    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    email_address = os.environ.get("ALERT_EMAIL_ADDRESS", "")
    smtp_server = os.environ.get("SMTP_SERVER", "")
    smtp_port = int(os.environ.get("SMTP_PORT", 465) or 465)
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    local_channel = channel
    if local_channel == "auto":
        if wechat_enabled and wechat_webhook:
            local_channel = "wechat"
        elif dingtalk_enabled and dingtalk_webhook:
            local_channel = "dingtalk"
        elif email_enabled and email_address:
            local_channel = "email"
        else:
            return {"status": "SUCCESS", "message": "当前系统所有的告警通知渠道均已关闭或未配置。告警内容已记录，未向外发送。"}

    try:
        if local_channel == "wechat":
            if not wechat_enabled:
                return {"status": "SUCCESS", "message": "企业微信通知已被拦截，因为系统默认禁用了该渠道。"}
            if not wechat_webhook:
                return {"status": "ERROR", "message": "企业微信 Webhook 未配置"}
            payload = {"msgtype": "markdown", "markdown": {"content": f"## {title}\n{content}"}}
            req = urllib.request.Request(wechat_webhook, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5)
            return {"status": "SUCCESS", "message": "企业微信通知已发送成功！"}

        elif local_channel == "dingtalk":
            if not dingtalk_enabled:
                return {"status": "SUCCESS", "message": "钉钉通知已被拦截，因为系统默认禁用了该渠道。"}
            if not dingtalk_webhook:
                return {"status": "ERROR", "message": "钉钉 Webhook 未配置"}
            payload = {"msgtype": "markdown", "markdown": {"title": title, "text": f"## {title}\n{content}"}}
            req = urllib.request.Request(dingtalk_webhook, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5)
            return {"status": "SUCCESS", "message": "钉钉通知已发送成功！"}

        elif local_channel == "email":
            if not email_enabled:
                return {"status": "SUCCESS", "message": "邮件通知已被拦截，因为系统默认禁用了该渠道。"}
            if not (email_address and smtp_server and smtp_user and smtp_pass):
                return {"status": "ERROR", "message": "邮件渠道尚未配置完整的 SMTP 参数"}

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = email_address
            msg['Subject'] = title
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, email_address, msg.as_string())
            server.quit()
            return {"status": "SUCCESS", "message": "邮件通知已发送成功！"}

        else:
            return {"status": "SUCCESS", "message": f"【通报完成】系统已捕获您发送给 {local_channel} 的报告。标题：{title}"}
    except Exception as e:
        return {"status": "ERROR", "message": f"通知发送失败: {str(e)}"}
