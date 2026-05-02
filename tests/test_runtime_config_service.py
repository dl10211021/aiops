import logging
import unittest
from unittest.mock import patch

from core.runtime_config_service import (
    DEFAULT_OPSCORE_HOST,
    DEFAULT_OPSCORE_PORT,
    get_allowed_origins,
    get_log_level,
    get_runtime_host,
    get_runtime_port,
)


class TestRuntimeConfigService(unittest.TestCase):
    def test_runtime_host_and_port_follow_environment(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(get_runtime_host(), DEFAULT_OPSCORE_HOST)
            self.assertEqual(get_runtime_port(), DEFAULT_OPSCORE_PORT)

        with patch.dict("os.environ", {"OPSCORE_HOST": "127.0.0.1", "OPSCORE_PORT": "9010"}, clear=True):
            self.assertEqual(get_runtime_host(), "127.0.0.1")
            self.assertEqual(get_runtime_port(), 9010)

    def test_runtime_port_rejects_invalid_values(self):
        for value in ("not-a-port", "0", "65536"):
            with self.subTest(value=value):
                with patch.dict("os.environ", {"OPSCORE_PORT": value}, clear=True):
                    with self.assertRaises(ValueError):
                        get_runtime_port()

    def test_log_level_defaults_to_info_for_unknown_values(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "debug"}, clear=True):
            self.assertEqual(get_log_level(), logging.DEBUG)

        with patch.dict("os.environ", {"LOG_LEVEL": "verbose"}, clear=True):
            self.assertEqual(get_log_level(), logging.INFO)

    def test_allowed_origins_are_trimmed_and_empty_values_removed(self):
        with patch.dict(
            "os.environ",
            {"OPSCORE_ALLOWED_ORIGINS": " http://localhost:8000, ,http://127.0.0.1:5173 "},
            clear=True,
        ):
            self.assertEqual(
                get_allowed_origins(),
                ["http://localhost:8000", "http://127.0.0.1:5173"],
            )


if __name__ == "__main__":
    unittest.main()
