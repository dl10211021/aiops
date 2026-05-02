import unittest
from unittest.mock import patch

from core.active_sessions_service import build_active_sessions_payload


class FakeMemoryDB:
    sensitive_keys = ["api_key"]


class TestActiveSessionsService(unittest.TestCase):
    def test_build_active_sessions_payload_uses_store_sensitive_keys(self):
        payload = build_active_sessions_payload(
            {
                "sid-1": {
                    "info": {
                        "host": "10.0.0.10",
                        "asset_type": "linux",
                        "protocol": "ssh",
                        "extra_args": {"api_key": "secret", "database": "ops"},
                    }
                }
            },
            is_session_streaming=lambda sid: sid == "sid-1",
            memory_db=FakeMemoryDB(),
        )

        self.assertEqual(payload["sid-1"]["extra_args"]["api_key"], "********")
        self.assertEqual(payload["sid-1"]["extra_args"]["database"], "ops")
        self.assertTrue(payload["sid-1"]["isStreaming"])

    def test_build_active_sessions_payload_uses_default_streaming_checker(self):
        with patch("core.active_sessions_service.chat_runs_module.is_chat_running", return_value=True):
            payload = build_active_sessions_payload(
                {
                    "sid-1": {
                        "info": {
                            "host": "10.0.0.10",
                            "asset_type": "linux",
                            "protocol": "ssh",
                            "extra_args": {},
                        }
                    }
                },
                memory_db=FakeMemoryDB(),
            )

        self.assertTrue(payload["sid-1"]["isStreaming"])


if __name__ == "__main__":
    unittest.main()
