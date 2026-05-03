import unittest

from core.session_runtime import (
    SessionRuntimeError,
    drain_all_pending_messages,
    drain_session_pending_messages,
    set_session_group,
    set_session_heartbeat,
    set_session_metadata,
    set_session_permission,
    set_session_skills,
)


class TestSessionRuntime(unittest.TestCase):
    def test_set_session_permission_updates_existing_session_info(self):
        sessions = {"sid-1": {"info": {"allow_modifications": False}}}

        info = set_session_permission(sessions, "sid-1", True)

        self.assertIs(info, sessions["sid-1"]["info"])
        self.assertTrue(sessions["sid-1"]["info"]["allow_modifications"])

    def test_set_session_heartbeat_sets_enabled_and_master_interval(self):
        sessions = {"sid-1": {"info": {}}}

        info = set_session_heartbeat(sessions, "sid-1", True, 180)

        self.assertTrue(info["heartbeat_enabled"])
        self.assertEqual(info["last_active"], 0)
        self.assertEqual(info["extra_args"]["master_interval"], 180)

    def test_set_session_heartbeat_preserves_last_active_when_disabled(self):
        sessions = {"sid-1": {"info": {"last_active": 123}}}

        info = set_session_heartbeat(sessions, "sid-1", False)

        self.assertFalse(info["heartbeat_enabled"])
        self.assertEqual(info["last_active"], 123)
        self.assertNotIn("extra_args", info)

    def test_missing_session_raises_typed_error(self):
        with self.assertRaises(SessionRuntimeError) as ctx:
            set_session_permission({}, "missing", True)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "会话不存在或已断开")

    def test_set_session_skills_updates_existing_session_info(self):
        sessions = {"sid-1": {"info": {"active_skills": []}}}
        selected_skills = ["linux-basic", "disk-check"]

        info = set_session_skills(sessions, "sid-1", selected_skills)

        self.assertIs(info, sessions["sid-1"]["info"])
        self.assertEqual(info["active_skills"], selected_skills)

    def test_drain_session_pending_messages_returns_and_clears_messages(self):
        messages = [{"role": "assistant", "content": "ok"}]
        sessions = {"sid-1": {"info": {"pending_messages": messages}}}

        drained = drain_session_pending_messages(sessions, "sid-1")

        self.assertIs(drained, messages)
        self.assertEqual(sessions["sid-1"]["info"]["pending_messages"], [])

    def test_drain_all_pending_messages_copies_and_clears_only_pending_sessions(self):
        messages = [{"role": "assistant", "content": "ok"}]
        sessions = {
            "sid-1": {"info": {"pending_messages": messages}},
            "sid-2": {"info": {"pending_messages": []}},
        }

        updates = drain_all_pending_messages(sessions)

        self.assertEqual(updates, {"sid-1": messages})
        self.assertIsNot(updates["sid-1"], messages)
        self.assertEqual(sessions["sid-1"]["info"]["pending_messages"], [])
        self.assertEqual(sessions["sid-2"]["info"]["pending_messages"], [])

    def test_set_session_group_updates_primary_tag_and_keeps_secondary_tags(self):
        sessions = {"sid-1": {"info": {"tags": ["旧组", "P0", "数据库核心组"]}}}

        info, group_name = set_session_group(sessions, "sid-1", " 数据库核心组 ")

        self.assertEqual(group_name, "数据库核心组")
        self.assertEqual(info["tags"], ["数据库核心组", "P0"])

    def test_set_session_group_rejects_blank_name_after_session_lookup(self):
        sessions = {"sid-1": {"info": {"tags": ["旧组"]}}}

        with self.assertRaises(SessionRuntimeError) as ctx:
            set_session_group(sessions, "sid-1", "   ")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "会话组名称不能为空")

    def test_set_session_metadata_updates_remark_group_and_secondary_tags(self):
        sessions = {
            "sid-1": {
                "info": {
                    "remark": "旧名称",
                    "tags": ["旧组", "P0", "数据库"],
                }
            }
        }

        info, group_name = set_session_metadata(
            sessions,
            "sid-1",
            remark="  核心 MySQL  ",
            group_name=" 数据库核心组 ",
            tags=["旧组", "P0", "数据库", "数据库核心组", "P0"],
        )

        self.assertEqual(group_name, "数据库核心组")
        self.assertEqual(info["remark"], "核心 MySQL")
        self.assertEqual(info["tags"], ["数据库核心组", "P0", "数据库"])

    def test_set_session_metadata_preserves_current_group_when_only_tags_change(self):
        sessions = {"sid-1": {"info": {"tags": ["生产组", "P0"]}}}

        info, group_name = set_session_metadata(
            sessions,
            "sid-1",
            tags=["P1", "数据库"],
        )

        self.assertEqual(group_name, "生产组")
        self.assertEqual(info["tags"], ["生产组", "P1", "数据库"])
