from __future__ import annotations

import os
import re
import time
from pathlib import Path


class CustomSkillStorageError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def resolve_custom_skill_dir(base_dir: Path, target_dir_name: str) -> Path:
    name = str(target_dir_name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise CustomSkillStorageError(
            422,
            "target_dir_name 只能包含英文字母、数字、横线和下划线。",
        )

    base = base_dir.resolve()
    target = (base / name).resolve()
    if target.parent != base:
        raise CustomSkillStorageError(422, "非法技能目标路径。")
    return target


def resolve_custom_skill_file(base_dir: Path, skill_id: str, file_name: str) -> Path:
    skill_dir = resolve_custom_skill_dir(base_dir, skill_id)
    safe_file = str(file_name or "").strip()
    if not safe_file or os.path.basename(safe_file) != safe_file:
        raise CustomSkillStorageError(422, "file_name 只能是文件名，不能包含路径。")
    target = (skill_dir / safe_file).resolve()
    if target.parent != skill_dir.resolve():
        raise CustomSkillStorageError(422, "非法技能文件路径。")
    return target


def resolve_custom_skill_version_file(base_dir: Path, skill_id: str, version_id: str) -> Path:
    skill_dir = resolve_custom_skill_dir(base_dir, skill_id)
    safe_version = str(version_id or "").strip()
    if not safe_version or os.path.basename(safe_version) != safe_version:
        raise CustomSkillStorageError(422, "version_id 只能是版本文件名。")
    versions_dir = (skill_dir / ".versions").resolve()
    target = (versions_dir / safe_version).resolve()
    if target.parent != versions_dir:
        raise CustomSkillStorageError(422, "非法版本文件路径。")
    return target


def atomic_replace_bytes(file_path: Path, content: bytes) -> None:
    tmp_path = file_path.with_name(f".{file_path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
