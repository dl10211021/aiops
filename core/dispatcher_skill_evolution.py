"""Skill evolution file operations for dispatcher tool execution."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.custom_skill_storage import CustomSkillStorageError, resolve_custom_skill_resource_file
from core.skill_lifecycle import validate_skill_candidate


def atomic_write_text(file_path: str, content: str) -> None:
    tmp_path = os.path.join(
        os.path.dirname(file_path),
        f".{os.path.basename(file_path)}.{time.time_ns()}.tmp",
    )
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def backup_existing_skill_file(file_path: str) -> str | None:
    if not os.path.exists(file_path):
        return None
    versions_dir = os.path.join(os.path.dirname(file_path), ".versions")
    os.makedirs(versions_dir, exist_ok=True)
    backup_name = f"{os.path.basename(file_path)}.{time.strftime('%Y%m%d%H%M%S')}.{time.time_ns()}.bak"
    backup_path = os.path.join(versions_dir, backup_name)
    with open(file_path, "rb") as source, open(backup_path, "wb") as target:
        target.write(source.read())
        target.flush()
        os.fsync(target.fileno())
    return backup_path


def execute_skill_evolution_tool(
    args: dict[str, Any],
    target_base: str,
    refresh_skills: Callable[[], Any],
    logger: logging.Logger | None = None,
) -> str:
    skill_id = str(args.get("skill_id", "") or "").strip()
    file_name = str(args.get("file_name", "") or "").strip()
    content = str(args.get("content", "") or "")

    os.makedirs(target_base, exist_ok=True)

    validation = validate_skill_candidate(skill_id, file_name, content, allow_nested=True)
    if not validation["valid"]:
        detail = "；".join(issue["message"] for issue in validation["issues"])
        return json.dumps({"error": detail}, ensure_ascii=False)

    safe_file_name = validation["file_name"]
    try:
        file_path = resolve_custom_skill_resource_file(Path(target_base), skill_id, safe_file_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = backup_existing_skill_file(str(file_path))
        atomic_write_text(str(file_path), content)
        if logger:
            logger.info("AI 成功自我进化：更新了文件 -> %s", file_path)

        refresh_skills()
        return json.dumps(
            {
                "status": "SUCCESS",
                "message": f"技能卡带文件 {file_name} 已经成功更新并热重载！现在您可以告诉用户它已经生效了。",
                "skill_id": skill_id,
                "file_name": safe_file_name,
                "file_path": str(file_path),
                "backup_path": backup_path,
            }
        )
    except CustomSkillStorageError as exc:
        return json.dumps({"error": exc.detail}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"写入文件失败: {str(exc)}"})
