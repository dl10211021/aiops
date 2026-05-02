from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core import dispatcher as dispatcher_module
from core import approval_queue
from core.custom_skill_storage import (
    CustomSkillStorageError,
    atomic_replace_bytes,
    resolve_custom_skill_file,
    resolve_custom_skill_version_file,
)


class CustomSkillRollbackServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def _load_rollback_candidate(
    base_dir: Path,
    dispatcher: Any,
    *,
    skill_id: str,
    file_name: str,
    version_id: str,
) -> dict[str, Any]:
    try:
        target_file = resolve_custom_skill_file(base_dir, skill_id, file_name)
        version_file = resolve_custom_skill_version_file(base_dir, skill_id, version_id)
    except CustomSkillStorageError as exc:
        raise CustomSkillRollbackServiceError(exc.status_code, exc.detail) from exc

    if not target_file.parent.exists():
        raise CustomSkillRollbackServiceError(404, "技能不存在。")
    if not version_file.is_file():
        raise CustomSkillRollbackServiceError(404, "版本不存在。")

    content = version_file.read_bytes()
    if target_file.name == "SKILL.md":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CustomSkillRollbackServiceError(422, "SKILL.md 版本必须是 UTF-8 文本。") from exc
        valid, reason = dispatcher._validate_skill_frontmatter(skill_id, text)
        if not valid:
            raise CustomSkillRollbackServiceError(422, reason)

    return {
        "target_file": target_file,
        "version_file": version_file,
        "content": content,
    }


def _request_rollback_approval(skill_id: str, target_file: Path, version_file: Path) -> dict[str, Any]:
    return approval_queue.record_approval_request(
        tool_call_id=f"rollback-{skill_id}-{int(time.time_ns())}",
        session_id="api",
        tool_name="rollback_skill",
        args={
            "skill_id": skill_id,
            "file_name": target_file.name,
            "version_id": version_file.name,
            "target_file": str(target_file),
            "version_file": str(version_file),
        },
        reason="用户请求回滚平台技能文件，必须人工审批并审计。",
        context={"asset_type": "platform", "protocol": "api", "trigger_source": "skills.rollback_api"},
    )


def _validate_rollback_approval(
    approval_id: str,
    *,
    skill_id: str,
    target_file: Path,
    version_file: Path,
) -> None:
    approval = approval_queue.get_approval_request(approval_id)
    if not approval:
        raise CustomSkillRollbackServiceError(404, "审批请求不存在。")
    if approval.get("tool_name") != "rollback_skill":
        raise CustomSkillRollbackServiceError(422, "审批请求类型不匹配。")
    if approval.get("status") != "approved":
        raise CustomSkillRollbackServiceError(409, "技能回滚审批尚未批准。")
    if approval.get("execution"):
        raise CustomSkillRollbackServiceError(409, "该技能回滚审批已经执行过。")

    approved_args = approval.get("args") or {}
    if (
        approved_args.get("skill_id") != skill_id
        or approved_args.get("file_name") != target_file.name
        or approved_args.get("version_id") != version_file.name
    ):
        raise CustomSkillRollbackServiceError(409, "审批请求与本次回滚目标不匹配。")


def rollback_custom_skill_version(
    base_dir: Path,
    dispatcher: Any | None = None,
    *,
    skill_id: str,
    file_name: str,
    version_id: str,
    approval_id: str | None = None,
) -> dict[str, Any]:
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    candidate = _load_rollback_candidate(
        base_dir,
        resolved_dispatcher,
        skill_id=skill_id,
        file_name=file_name,
        version_id=version_id,
    )
    target_file = candidate["target_file"]
    version_file = candidate["version_file"]
    content = candidate["content"]

    if not approval_id:
        approval = _request_rollback_approval(skill_id, target_file, version_file)
        return {
            "status": "pending_approval",
            "message": "技能回滚已进入审批队列，审批通过后请携带 approval_id 再次提交。",
            "data": {"approval": approval, "approval_id": approval["id"]},
        }

    _validate_rollback_approval(
        approval_id,
        skill_id=skill_id,
        target_file=target_file,
        version_file=version_file,
    )

    backup_path = resolved_dispatcher._backup_existing_skill_file(str(target_file))
    atomic_replace_bytes(target_file, content)
    resolved_dispatcher.refresh_skills(force=True)

    result = {
        "status": "SUCCESS",
        "skill_id": skill_id,
        "file_name": file_name,
        "file_path": str(target_file),
        "backup_path": backup_path,
        "version_id": version_id,
        "restored_version_path": str(version_file),
    }
    try:
        approval_queue.record_approval_execution(approval_id, json.dumps(result, ensure_ascii=False))
    except KeyError:
        pass

    return {
        "status": "success",
        "message": f"技能文件 {file_name} 已回滚到版本 {version_id}",
        "data": result,
    }
