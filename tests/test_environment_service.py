import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch

from core.environment_service import load_dotenv_if_available


class TestEnvironmentService(unittest.TestCase):
    def test_load_dotenv_if_available_loads_env_next_to_app_file(self):
        fake_dotenv = ModuleType("dotenv")
        fake_dotenv.load_dotenv = Mock()

        with (
            patch.dict(sys.modules, {"dotenv": fake_dotenv}),
            patch("core.environment_service.os.path.exists", return_value=True),
        ):
            loaded = load_dotenv_if_available("D:/app/main.py")

        self.assertTrue(loaded)
        fake_dotenv.load_dotenv.assert_called_once_with("D:/app\\.env", override=True)

    def test_load_dotenv_if_available_skips_missing_env_file(self):
        fake_dotenv = ModuleType("dotenv")
        fake_dotenv.load_dotenv = Mock()

        with (
            patch.dict(sys.modules, {"dotenv": fake_dotenv}),
            patch("core.environment_service.os.path.exists", return_value=False),
        ):
            loaded = load_dotenv_if_available("D:/app/main.py")

        self.assertFalse(loaded)
        fake_dotenv.load_dotenv.assert_not_called()

    def test_load_dotenv_if_available_skips_when_dependency_missing(self):
        with patch.dict(sys.modules, {"dotenv": None}):
            loaded = load_dotenv_if_available("D:/app/main.py")

        self.assertFalse(loaded)


if __name__ == "__main__":
    unittest.main()
