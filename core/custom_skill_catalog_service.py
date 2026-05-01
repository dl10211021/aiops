from __future__ import annotations

from pathlib import Path
from typing import Any


class CustomSkillCatalogServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def scan_custom_skill_catalog(dispatcher: Any) -> dict[str, str]:
    dispatcher.refresh_skills(force=True)
    return {"message": "扫描完成！本地技能库已更新。"}


def list_custom_skill_catalog(dispatcher: Any) -> dict[str, list[dict[str, Any]]]:
    registry = dispatcher.get_all_registered_skills()
    market = dispatcher.get_market_skills()
    return {"registry": registry + market}


def get_custom_skill_detail(dispatcher: Any, skill_id: str) -> dict[str, str]:
    if skill_id in dispatcher.skills_registry:
        skill = dispatcher.skills_registry[skill_id]
        return {
            "instructions": skill["instructions"],
            "source_path": skill["source_path"],
        }

    for skill in dispatcher.get_market_skills():
        if skill["id"] == skill_id:
            content = (Path(skill["source_path"]) / "SKILL.md").read_text(encoding="utf-8")
            return {
                "instructions": content,
                "source_path": skill["source_path"],
            }

    raise CustomSkillCatalogServiceError(404, "找不到该技能")
