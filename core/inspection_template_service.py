from __future__ import annotations

from typing import Any

from core.inspection_templates import delete_template, list_templates, save_template


class InspectionTemplateServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_inspection_template_records() -> list[dict[str, Any]]:
    return list_templates()


def save_inspection_template_record(
    payload: dict[str, Any],
    template_id: str | None = None,
) -> dict[str, Any]:
    template = dict(payload)
    if template_id is not None:
        template["id"] = template_id
    try:
        return save_template(template)
    except ValueError as exc:
        raise InspectionTemplateServiceError(422, str(exc)) from exc


def remove_inspection_template_record(template_id: str) -> None:
    if not delete_template(template_id):
        raise InspectionTemplateServiceError(404, "巡检模板不存在")
