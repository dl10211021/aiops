from __future__ import annotations

from pathlib import Path
from typing import Any

from core.custom_skill_storage import (
    CustomSkillStorageError,
    resolve_custom_skill_file,
)


class CustomSkillVersionServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _version_record_sort_key(record: dict[str, Any]) -> tuple[str, int, float, str]:
    prefix = f"{record['file_name']}."
    suffix = ".bak"
    version_part = record["id"][len(prefix) : -len(suffix)]
    timestamp, _, sequence = version_part.partition(".")
    try:
        sequence_number = int(sequence)
    except ValueError:
        sequence_number = -1
    return timestamp, sequence_number, record["created_at_ts"], record["id"]


def list_custom_skill_version_records(
    base_dir: Path,
    skill_id: str,
    file_name: str = "SKILL.md",
) -> list[dict[str, Any]]:
    try:
        skill_file = resolve_custom_skill_file(base_dir, skill_id, file_name)
    except CustomSkillStorageError as exc:
        raise CustomSkillVersionServiceError(exc.status_code, exc.detail) from exc

    versions_dir = skill_file.parent / ".versions"
    if not skill_file.parent.exists():
        raise CustomSkillVersionServiceError(404, "技能不存在。")

    versions: list[dict[str, Any]] = []
    if versions_dir.exists():
        prefix = f"{skill_file.name}."
        suffix = ".bak"
        for item in versions_dir.iterdir():
            if not item.is_file() or not item.name.startswith(prefix) or not item.name.endswith(suffix):
                continue
            stat = item.stat()
            versions.append(
                {
                    "id": item.name,
                    "file_name": skill_file.name,
                    "size": stat.st_size,
                    "created_at_ts": stat.st_mtime,
                }
            )
    versions.sort(key=_version_record_sort_key, reverse=True)
    return versions
