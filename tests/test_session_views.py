import unittest

from core.session_views import (
    build_active_session_view,
    build_active_sessions_response,
    mask_sensitive_extra_args,
)


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

    def test_build_active_sessions_response_indexes_sessions_by_id(self):
        response = build_active_sessions_response(
            {
                "sid-1": {
                    "info": {
                        "host": "10.0.0.10",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "extra_args": {"api_key": "secret"},
                        "tags": ["生产组"],
                    }
                },
                "sid-2": {
                    "info": {
                        "host": "10.0.0.20",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "extra_args": {},
                    }
                },
            },
            is_session_streaming=lambda sid: sid == "sid-2",
            sensitive_keys=["api_key"],
        )

        self.assertEqual(set(response), {"sid-1", "sid-2"})
        self.assertEqual(response["sid-1"]["extra_args"]["api_key"], "********")
        self.assertFalse(response["sid-1"]["isStreaming"])
        self.assertTrue(response["sid-2"]["isStreaming"])


if __name__ == "__main__":
    unittest.main()
