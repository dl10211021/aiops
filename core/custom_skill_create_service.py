from __future__ import annotations

from pathlib import Path
from typing import Any

from core import dispatcher as dispatcher_module
from core.custom_skill_storage import (
    CustomSkillStorageError,
    atomic_replace_bytes,
    resolve_custom_skill_dir,
)
from core.skill_lifecycle import validate_skill_candidate


class CustomSkillCreateServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def reject_invalid_skill_candidate(validation: dict[str, Any]) -> None:
    if validation["valid"]:
        return
    detail = "；".join(issue["message"] for issue in validation["issues"])
    raise CustomSkillCreateServiceError(422, detail or "技能校验失败。")


def create_custom_skill_record(
    base_dir: Path,
    dispatcher: Any | None = None,
    *,
    skill_id: str,
    description: str,
    instructions: str,
    script_name: str | None = None,
    script_content: str | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    md_content = f"---\nname: {skill_id}\ndescription: {description}\n---\n\n{instructions}\n"
    reject_invalid_skill_candidate(validate_skill_candidate(skill_id, "SKILL.md", md_content))

    script_validation = None
    if script_name or script_content:
        if not script_name or script_content is None:
            raise CustomSkillCreateServiceError(422, "脚本名称和脚本内容必须同时提供。")
        script_validation = validate_skill_candidate(skill_id, script_name, script_content)
        reject_invalid_skill_candidate(script_validation)

    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        dest_path = resolve_custom_skill_dir(base_dir, skill_id)

        if dest_path.exists() and not overwrite_existing:
            raise CustomSkillCreateServiceError(
                409,
                f"该技能包 ID ({skill_id}) 已存在，请换一个名称。",
            )

        backup_paths: list[str] = []
        if dest_path.exists():
            skill_backup = resolved_dispatcher._backup_existing_skill_file(str(dest_path / "SKILL.md"))
            if skill_backup:
                backup_paths.append(skill_backup)
        else:
            dest_path.mkdir()

        atomic_replace_bytes(dest_path / "SKILL.md", md_content.encode("utf-8"))

        if script_validation:
            script_path = dest_path / script_validation["file_name"]
            script_backup = resolved_dispatcher._backup_existing_skill_file(str(script_path))
            if script_backup:
                backup_paths.append(script_backup)
            atomic_replace_bytes(script_path, script_content.encode("utf-8"))

        resolved_dispatcher.refresh_skills(force=True)

        action = "更新" if overwrite_existing else "创建"
        return {
            "message": f"定制技能 {skill_id} {action}成功，已自动加载就绪！",
            "data": {
                "skill_id": skill_id,
                "skill_path": str(dest_path),
                "backup_paths": backup_paths,
                "updated": bool(overwrite_existing),
            },
        }
    except CustomSkillCreateServiceError:
        raise
    except CustomSkillStorageError as exc:
        raise CustomSkillCreateServiceError(exc.status_code, exc.detail) from exc
    except Exception as exc:
        raise CustomSkillCreateServiceError(500, str(exc)) from exc
