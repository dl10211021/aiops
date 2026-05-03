from pathlib import Path

from fastapi import APIRouter

from api.errors import raise_http_error
from api.response_mappers.skills import (
    custom_skill_create_kwargs,
    custom_skill_migration_kwargs,
    custom_skill_rollback_kwargs,
    skill_created_response_kwargs,
    skill_detail_response_kwargs,
    skill_migration_response_kwargs,
    skill_registry_response_kwargs,
    skill_rollback_response_kwargs,
    skill_scan_response_kwargs,
    skill_validation_response_kwargs,
    skill_versions_response_kwargs,
)
from api.schemas import (
    CreateSkillRequest,
    MigrateRequest,
    ResponseModel,
    SkillRollbackRequest,
    SkillValidationRequest,
)
from core.custom_skill_catalog_service import (
    CustomSkillCatalogServiceError,
    get_custom_skill_detail as get_custom_skill_detail_record,
    list_custom_skill_catalog,
    scan_custom_skill_catalog,
)
from core.custom_skill_create_service import (
    CustomSkillCreateServiceError,
    create_custom_skill_record,
)
from core.custom_skill_migration_service import (
    CustomSkillMigrationServiceError,
    migrate_custom_skill_record,
)
from core.custom_skill_rollback_service import (
    CustomSkillRollbackServiceError,
    rollback_custom_skill_version as rollback_custom_skill_version_record,
)
from core.custom_skill_version_service import (
    CustomSkillVersionServiceError,
    list_custom_skill_version_records,
)
from core.skill_lifecycle import validate_skill_candidate


CUSTOM_SKILLS_DIR = Path(__file__).resolve().parent.parent / "my_custom_skills"
router = APIRouter()


@router.post("/skills/scan", response_model=ResponseModel)
async def scan_skills():
    """【新功能】前端手动触发扫描本地磁盘目录，热加载新的技能"""
    result = scan_custom_skill_catalog()
    return ResponseModel(**skill_scan_response_kwargs(result))


@router.get("/skills/registry", response_model=ResponseModel)
async def get_skill_registry():
    """【新功能】前端调用，获取所有已安装的技能卡带摘要以及外部市场待下载的卡带"""
    return ResponseModel(
        **skill_registry_response_kwargs(list_custom_skill_catalog())
    )


@router.get("/skills/registry/{skill_id}", response_model=ResponseModel)
async def get_skill_detail(skill_id: str):
    """【新功能】前端调用，获取某个特定技能卡带的完整 Markdown 原文"""
    try:
        detail = get_custom_skill_detail_record(skill_id)
    except CustomSkillCatalogServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**skill_detail_response_kwargs(detail))


@router.post("/skills/create", response_model=ResponseModel)
async def create_skill(req: CreateSkillRequest):
    """【新功能】用户在页面上手动创建新的定制技能卡带"""
    try:
        result = create_custom_skill_record(
            CUSTOM_SKILLS_DIR,
            **custom_skill_create_kwargs(req),
        )
    except CustomSkillCreateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**skill_created_response_kwargs(result))


@router.post("/skills/validate", response_model=ResponseModel)
async def validate_skill(req: SkillValidationRequest):
    """静态校验技能文件内容，不写文件、不执行脚本。"""
    result = validate_skill_candidate(req.skill_id, req.file_name, req.content)
    return ResponseModel(**skill_validation_response_kwargs(result))


@router.get("/skills/{skill_id}/versions", response_model=ResponseModel)
async def list_skill_versions(skill_id: str, file_name: str = "SKILL.md"):
    """列出 my_custom_skills 中某个技能文件的可回滚版本。"""
    try:
        versions = list_custom_skill_version_records(
            CUSTOM_SKILLS_DIR,
            skill_id,
            file_name,
        )
    except CustomSkillVersionServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**skill_versions_response_kwargs(versions))


@router.post("/skills/{skill_id}/rollback", response_model=ResponseModel)
async def rollback_skill_version(skill_id: str, req: SkillRollbackRequest):
    """将 my_custom_skills 中的技能文件回滚到指定备份版本。"""
    try:
        result = rollback_custom_skill_version_record(
            CUSTOM_SKILLS_DIR,
            skill_id=skill_id,
            **custom_skill_rollback_kwargs(req),
        )
    except CustomSkillRollbackServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**skill_rollback_response_kwargs(result))


@router.post("/skills/migrate", response_model=ResponseModel)
async def migrate_skill(req: MigrateRequest):
    """将外部卡带拷贝到专属的 my_custom_skills 目录"""
    try:
        result = migrate_custom_skill_record(
            CUSTOM_SKILLS_DIR,
            **custom_skill_migration_kwargs(req),
        )
    except CustomSkillMigrationServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**skill_migration_response_kwargs(result))
