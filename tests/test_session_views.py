import unittest

from core.session_views import build_active_session_view, mask_sensitive_extra_args


class TestSessionViews(unittest.TestCase):
    def test_mask_sensitive_extra_args_replaces_configured_keys_only(self):
        self.assertEqual(
            mask_sensitive_extra_args(
                {"api_key": "secret", "database": "ops"},
                ["api_key"],
            ),
            {"api_key": "********", "database": "ops"},
        )

    def test_build_active_session_view_keeps_existing_contract_and_group_name(self):
        view = build_active_session_view(
            "sid-1",
            {
                "host": "10.0.0.10",
                "port": 22,
                "username": "root",
                "remark": "核心主机",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {"api_key": "secret"},
                "allow_modifications": False,
                "active_skills": ["linux"],
                "agent_profile": "dba",
                "heartbeat_enabled": True,
                "tags": ["生产组", "P0"],
                "target_scope": "asset",
            },
            is_streaming=True,
            sensitive_keys=["api_key"],
        )

        self.assertEqual(view["id"], "sid-1")
        self.assertEqual(view["protocol"], "ssh")
        self.assertEqual(view["group_name"], "生产组")
        self.assertEqual(view["tags"], ["生产组", "P0"])
        self.assertEqual(view["extra_args"]["api_key"], "********")
        self.assertTrue(view["isStreaming"])


if __name__ == "__main__":
    unittest.main()
