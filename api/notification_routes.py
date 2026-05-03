import logging

from fastapi import APIRouter, HTTPException

from api.errors import raise_http_error
from api.response_mappers.notifications import (
    notification_channel_test_response_kwargs,
    notification_config_response_kwargs,
    notification_config_saved_response_kwargs,
)
from api.schemas import NotificationConfigRequest, ResponseModel, TestNotificationRequest
from core.notification_config import build_notification_config
from core.notification_config_service import save_notification_config_record
from core.notification_test import (
    NotificationTestError,
    send_notification_channel_test,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/config/notifications", response_model=ResponseModel)
async def get_notification_config():
    """【新功能】获取当前的告警通道配置"""
    config = build_notification_config()
    return ResponseModel(**notification_config_response_kwargs(config))


@router.post("/config/notifications", response_model=ResponseModel)
async def update_notification_config(req: NotificationConfigRequest):
    """【新功能】前端动态配置企业微信/钉钉告警机器人 Webhook 及邮件"""
    try:
        save_notification_config_record(req.model_dump())
    except Exception as e:
        logger.error(f"Failed to save .env file: {e}")

    logger.info("Notification Webhooks updated.")
    return ResponseModel(**notification_config_saved_response_kwargs())


@router.post("/config/notifications/test", response_model=ResponseModel)
async def test_notification_channel(req: TestNotificationRequest):
    """【新功能】测试通知渠道"""
    try:
        message = send_notification_channel_test(req.channel)
        return ResponseModel(**notification_channel_test_response_kwargs(message))
    except NotificationTestError as exc:
        raise_http_error(exc)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"测试发送失败: {str(e)}") from e
