from __future__ import annotations

from pathlib import Path
from typing import Any

from core import dispatcher as dispatcher_module


class CustomSkillCatalogServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def scan_custom_skill_catalog(dispatcher: Any | None = None) -> dict[str, str]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    resolved_dispatcher.refresh_skills(force=True)
    return {"message": "扫描完成！本地技能库已更新。"}


def list_custom_skill_catalog(dispatcher: Any | None = None) -> dict[str, list[dict[str, Any]]]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    registry = resolved_dispatcher.get_all_registered_skills()
    market = resolved_dispatcher.get_market_skills()
    return {"registry": registry + market}


def get_custom_skill_detail(skill_id: str, dispatcher: Any | None = None) -> dict[str, str]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    if skill_id in resolved_dispatcher.skills_registry:
        skill = resolved_dispatcher.skills_registry[skill_id]
        return {
            "instructions": skill["instructions"],
            "source_path": skill["source_path"],
        }

    for skill in resolved_dispatcher.get_market_skills():
        if skill["id"] == skill_id:
            content = (Path(skill["source_path"]) / "SKILL.md").read_text(encoding="utf-8")
            return {
                "instructions": content,
                "source_path": skill["source_path"],
            }

    raise CustomSkillCatalogServiceError(404, "找不到该技能")
