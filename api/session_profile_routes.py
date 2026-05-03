from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.session import (
    session_profile_generate_kwargs,
    session_profile_generated_response_kwargs,
    session_profile_response_kwargs,
)
from api.schema_models.common import ResponseModel
from api.schema_models.sessions import SessionProfileGenerateRequest
from core.session_inspection_response import build_inspection_response_payload
from core.session_inspection_service import inspect_active_session_record
from core.session_profile_service import (
    SessionProfileServiceError,
    generate_session_profile_record,
    get_session_profile_record,
)


router = APIRouter()


@router.post("/session/{session_id}/inspect", response_model=ResponseModel)
async def inspect_active_session(session_id: str):
    """对已建立的会话执行只读巡检。"""
    report = await inspect_active_session_record(session_id)
    return ResponseModel(**build_inspection_response_payload(report))


@router.get("/session/{session_id}/profile", response_model=ResponseModel)
async def get_active_session_profile(session_id: str):
    """读取当前会话沉淀的资产画像。"""
    profile = await get_session_profile_record(session_id)
    return ResponseModel(**session_profile_response_kwargs(profile))


@router.post("/session/{session_id}/profile/generate", response_model=ResponseModel)
async def generate_active_session_profile(
    session_id: str,
    req: SessionProfileGenerateRequest,
):
    """基于会话历史和只读巡检生成资产画像，并写入独立画像记忆。"""
    try:
        profile = await generate_session_profile_record(
            session_id,
            **session_profile_generate_kwargs(req),
        )
    except SessionProfileServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**session_profile_generated_response_kwargs(profile))
