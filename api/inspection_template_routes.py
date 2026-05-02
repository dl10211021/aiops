from fastapi import APIRouter

from api.errors import raise_http_error
from api.mappers import (
    inspection_template_deleted_response_kwargs,
    inspection_template_list_response_kwargs,
    inspection_template_save_payload,
    inspection_template_saved_response_kwargs,
)
from api.schemas import InspectionTemplatePayload, ResponseModel
from core.inspection_template_service import (
    InspectionTemplateServiceError,
    list_inspection_template_records,
    remove_inspection_template_record,
    save_inspection_template_record,
)


router = APIRouter()


@router.get("/inspection-templates", response_model=ResponseModel)
async def list_inspection_templates():
    """列出内置与自定义巡检模板。"""
    return ResponseModel(
        **inspection_template_list_response_kwargs(list_inspection_template_records())
    )


@router.post("/inspection-templates", response_model=ResponseModel)
async def create_inspection_template(req: InspectionTemplatePayload):
    """创建巡检模板；模板必须通过只读安全校验。"""
    try:
        template = save_inspection_template_record(inspection_template_save_payload(req))
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        **inspection_template_saved_response_kwargs(template, "巡检模板已保存")
    )


@router.put("/inspection-templates/{template_id}", response_model=ResponseModel)
async def update_inspection_template(template_id: str, req: InspectionTemplatePayload):
    """更新巡检模板；路径 ID 优先，避免请求体误改主键。"""
    try:
        template = save_inspection_template_record(
            inspection_template_save_payload(req),
            template_id,
        )
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(
        **inspection_template_saved_response_kwargs(template, "巡检模板已更新")
    )


@router.delete("/inspection-templates/{template_id}", response_model=ResponseModel)
async def delete_inspection_template(template_id: str):
    """删除巡检模板。"""
    try:
        remove_inspection_template_record(template_id)
    except InspectionTemplateServiceError as exc:
        raise_http_error(exc)
    return ResponseModel(**inspection_template_deleted_response_kwargs())
