from __future__ import annotations

import os
import re
import time
from pathlib import Path


ALLOWED_NESTED_SKILL_DIRS = {
    "agents",
    "assets",
    "eval-viewer",
    "evals",
    "references",
    "scripts",
}


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


def normalize_custom_skill_file_name(file_name: str, *, allow_nested: bool = False) -> str:
    safe_file = str(file_name or "").strip().replace("\\", "/")
    if not safe_file:
        raise CustomSkillStorageError(422, "file_name 不能为空。")
    if re.match(r"^[A-Za-z]:", safe_file) or safe_file.startswith("/"):
        raise CustomSkillStorageError(422, "非法文件名：file_name 不能包含绝对路径或盘符。")

    parts = [part for part in safe_file.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise CustomSkillStorageError(422, "非法文件名：file_name 不能包含空路径、. 或 ..。")

    if len(parts) == 1:
        return parts[0]

    if not allow_nested:
        raise CustomSkillStorageError(422, "非法文件名：file_name 只能是文件名，不能包含路径。")

    if parts[0] not in ALLOWED_NESTED_SKILL_DIRS:
        allowed = "、".join(sorted(ALLOWED_NESTED_SKILL_DIRS))
        raise CustomSkillStorageError(
            422,
            f"非法资源路径：嵌套文件只能位于 {allowed} 目录。",
        )

    if any(re.search(r'[<>:"|?*]', part) for part in parts):
        raise CustomSkillStorageError(422, "非法文件名：file_name 包含系统保留字符。")

    return "/".join(parts)


def resolve_custom_skill_resource_file(base_dir: Path, skill_id: str, file_name: str) -> Path:
    skill_dir = resolve_custom_skill_dir(base_dir, skill_id)
    relative_name = normalize_custom_skill_file_name(file_name, allow_nested=True)
    target = (skill_dir / Path(*relative_name.split("/"))).resolve()
    resolved_skill_dir = skill_dir.resolve()
    try:
        common = os.path.commonpath([str(resolved_skill_dir), str(target)])
    except ValueError as exc:
        raise CustomSkillStorageError(422, "非法技能资源路径。") from exc
    if common != str(resolved_skill_dir):
        raise CustomSkillStorageError(422, "非法技能资源路径。")
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
