import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import approval_queue
from core.custom_skill_rollback_service import (
    CustomSkillRollbackServiceError,
    rollback_custom_skill_version,
)
from core.skill_lifecycle import validate_skill_frontmatter


def temporary_workspace():
    temp_root = Path.cwd() / ".tmp" / "tests"
    temp_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=temp_root)


class FakeDispatcher:
    def __init__(self):
        self.refresh_calls = []

    def _validate_skill_frontmatter(self, skill_id, content):
        return validate_skill_frontmatter(skill_id, content)

    def _backup_existing_skill_file(self, file_path):
        target = Path(file_path)
        if not target.exists():
            return None
        versions_dir = target.parent / ".versions"
        versions_dir.mkdir(exist_ok=True)
        backup_path = versions_dir / f"{target.name}.test.bak"
        backup_path.write_bytes(target.read_bytes())
        return str(backup_path)

    def refresh_skills(self, force=False):
        self.refresh_calls.append(force)


class TestCustomSkillRollbackService(unittest.TestCase):
    def _write_skill_with_version(self, root: Path) -> tuple[Path, str, str, str]:
        base_dir = root / "custom"
        skill_dir = base_dir / "safe-skill"
        versions_dir = skill_dir / ".versions"
        versions_dir.mkdir(parents=True)
        current = "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n"
        previous = "---\nname: safe-skill\ndescription: previous\n---\n\nprevious\n"
        (skill_dir / "SKILL.md").write_text(current, encoding="utf-8")
        version_id = "SKILL.md.20260428010101.1.bak"
        (versions_dir / version_id).write_text(previous, encoding="utf-8")
        return base_dir, version_id, current, previous

    def test_requests_approval_without_mutating_skill_file(self):
        with temporary_workspace() as tmp:
            root = Path(tmp)
            base_dir, version_id, current, _previous = self._write_skill_with_version(root)
            store_path = root / "approvals.json"

            with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
                result = rollback_custom_skill_version(
                    base_dir,
                    FakeDispatcher(),
                    skill_id="safe-skill",
                    file_name="SKILL.md",
                    version_id=version_id,
                )
                approval = approval_queue.get_approval_request(result["data"]["approval_id"])

            self.assertEqual(result["status"], "pending_approval")
            self.assertEqual((base_dir / "safe-skill" / "SKILL.md").read_text(encoding="utf-8"), current)
            self.assertEqual(approval["tool_name"], "rollback_skill")
            self.assertEqual(approval["args"]["skill_id"], "safe-skill")
            self.assertEqual(approval["args"]["version_id"], version_id)

    def test_rollback_request_uses_default_dispatcher_when_not_injected(self):
        with temporary_workspace() as tmp:
            root = Path(tmp)
            base_dir, version_id, current, _previous = self._write_skill_with_version(root)
            store_path = root / "approvals.json"
            dispatcher = FakeDispatcher()

            with (
                patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path),
                patch("core.dispatcher.dispatcher", dispatcher),
            ):
                result = rollback_custom_skill_version(
                    base_dir,
                    skill_id="safe-skill",
                    file_name="SKILL.md",
                    version_id=version_id,
                )

            self.assertEqual(result["status"], "pending_approval")
            self.assertEqual((base_dir / "safe-skill" / "SKILL.md").read_text(encoding="utf-8"), current)

    def test_approved_request_restores_version_once_and_audits_execution(self):
        with temporary_workspace() as tmp:
            root = Path(tmp)
            base_dir, version_id, current, previous = self._write_skill_with_version(root)
            store_path = root / "approvals.json"
            dispatcher = FakeDispatcher()

            with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
                pending = rollback_custom_skill_version(
                    base_dir,
                    dispatcher,
                    skill_id="safe-skill",
                    file_name="SKILL.md",
                    version_id=version_id,
                )
                approval_queue.resolve_approval_request(
                    pending["data"]["approval_id"],
                    approved=True,
                    operator="ops-admin",
                )
                restored = rollback_custom_skill_version(
                    base_dir,
                    dispatcher,
                    skill_id="safe-skill",
                    file_name="SKILL.md",
                    version_id=version_id,
                    approval_id=pending["data"]["approval_id"],
                )
                approval = approval_queue.get_approval_request(pending["data"]["approval_id"])
                with self.assertRaises(CustomSkillRollbackServiceError) as repeat_ctx:
                    rollback_custom_skill_version(
                        base_dir,
                        dispatcher,
                        skill_id="safe-skill",
                        file_name="SKILL.md",
                        version_id=version_id,
                        approval_id=pending["data"]["approval_id"],
                    )

            backup_path = Path(restored["data"]["backup_path"])
            self.assertEqual(restored["status"], "success")
            self.assertEqual((base_dir / "safe-skill" / "SKILL.md").read_text(encoding="utf-8"), previous)
            self.assertEqual(backup_path.read_text(encoding="utf-8"), current)
            self.assertEqual(dispatcher.refresh_calls, [True])
            self.assertEqual(approval["execution"]["artifacts"]["version_id"], version_id)
            self.assertEqual(repeat_ctx.exception.status_code, 409)

    def test_rejects_unapproved_or_mismatched_approval(self):
        with temporary_workspace() as tmp:
            root = Path(tmp)
            base_dir, version_id, _current, _previous = self._write_skill_with_version(root)
            store_path = root / "approvals.json"

            with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
                pending = rollback_custom_skill_version(
                    base_dir,
                    FakeDispatcher(),
                    skill_id="safe-skill",
                    file_name="SKILL.md",
                    version_id=version_id,
                )
                with self.assertRaises(CustomSkillRollbackServiceError) as pending_ctx:
                    rollback_custom_skill_version(
                        base_dir,
                        FakeDispatcher(),
                        skill_id="safe-skill",
                        file_name="SKILL.md",
                        version_id=version_id,
                        approval_id=pending["data"]["approval_id"],
                    )
                approval_queue.resolve_approval_request(
                    pending["data"]["approval_id"],
                    approved=True,
                    operator="ops-admin",
                )
                with self.assertRaises(CustomSkillRollbackServiceError) as mismatch_ctx:
                    rollback_custom_skill_version(
                        base_dir,
                        FakeDispatcher(),
                        skill_id="safe-skill",
                        file_name="notes.md",
                        version_id=version_id,
                        approval_id=pending["data"]["approval_id"],
                    )

            self.assertEqual(pending_ctx.exception.status_code, 409)
            self.assertEqual(mismatch_ctx.exception.status_code, 409)

    def test_validates_skill_md_content_before_requesting_approval(self):
        with temporary_workspace() as tmp:
            root = Path(tmp)
            base_dir, version_id, current, _previous = self._write_skill_with_version(root)
            (base_dir / "safe-skill" / ".versions" / version_id).write_text("missing frontmatter", encoding="utf-8")
            store_path = root / "approvals.json"

            with patch.object(approval_queue, "APPROVAL_STORE_PATH", store_path):
                with self.assertRaises(CustomSkillRollbackServiceError) as ctx:
                    rollback_custom_skill_version(
                        base_dir,
                        FakeDispatcher(),
                        skill_id="safe-skill",
                        file_name="SKILL.md",
                        version_id=version_id,
                    )

            self.assertEqual(ctx.exception.status_code, 422)
            self.assertEqual((base_dir / "safe-skill" / "SKILL.md").read_text(encoding="utf-8"), current)
            self.assertFalse(store_path.exists())


if __name__ == "__main__":
    unittest.main()
