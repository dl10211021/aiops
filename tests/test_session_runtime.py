import unittest

from core.session_runtime import (
    SessionRuntimeError,
    set_session_heartbeat,
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
