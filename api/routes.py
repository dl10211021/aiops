from fastapi import APIRouter
from api.system_info_routes import router as system_info_router
from api.knowledge_routes import router as knowledge_router
from api.alert_routes import router as alert_router
from api.dashboard_routes import router as dashboard_router
from api.protocol_verification_routes import router as protocol_verification_router
from api.notification_routes import router as notification_router
from api.config_routes import router as config_router
from api.approval_routes import router as approval_router
from api.connection_routes import router as connection_router
from api.skill_routes import router as skill_router
from api.asset_routes import router as asset_router
from api.session_runtime_routes import router as session_runtime_router
from api.session_history_routes import router as session_history_router
from api.session_profile_routes import router as session_profile_router
from api.session_webhook_routes import router as session_webhook_router
from api.custom_command_routes import router as custom_command_router
from api.inspection_template_routes import router as inspection_template_router
from api.inspection_job_routes import router as inspection_job_router
from api.inspection_run_routes import router as inspection_run_router
from api.chat_routes import router as chat_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(system_info_router)
router.include_router(knowledge_router)
router.include_router(alert_router)
router.include_router(dashboard_router)
router.include_router(protocol_verification_router)
router.include_router(notification_router)
router.include_router(config_router)
router.include_router(approval_router)
router.include_router(connection_router)
router.include_router(skill_router)
router.include_router(asset_router)
router.include_router(session_runtime_router)
router.include_router(session_history_router)
router.include_router(session_profile_router)
router.include_router(session_webhook_router)
router.include_router(custom_command_router)
router.include_router(inspection_template_router)
router.include_router(inspection_job_router)
router.include_router(inspection_run_router)

