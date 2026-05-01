from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from core.custom_skill_storage import CustomSkillStorageError, resolve_custom_skill_dir


class CustomSkillMigrationServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def migrate_custom_skill_record(
    base_dir: Path,
    dispatcher: Any,
    *,
    source_path: str,
    target_dir_name: str,
) -> dict[str, str]:
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        dest_path = resolve_custom_skill_dir(base_dir, target_dir_name)
    except CustomSkillStorageError as exc:
        raise CustomSkillMigrationServiceError(exc.status_code, exc.detail) from exc

    source = Path(source_path).expanduser().resolve()
    if not source.is_dir():
        raise CustomSkillMigrationServiceError(422, "source_path 必须是技能目录。")
    if not (source / "SKILL.md").is_file():
        raise CustomSkillMigrationServiceError(422, "source_path 必须包含 SKILL.md。")

    try:
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(source, dest_path)
        dispatcher.refresh_skills(force=True)
    except Exception as exc:
        raise CustomSkillMigrationServiceError(500, str(exc)) from exc

    return {
        "message": f"卡带 {target_dir_name} 已成功导入专属库！",
        "skill_path": str(dest_path),
    }
