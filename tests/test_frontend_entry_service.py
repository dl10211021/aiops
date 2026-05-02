import unittest
from unittest.mock import mock_open, patch

from core.frontend_entry_service import (
    get_legacy_static_dir,
    get_react_assets_dir,
    resolve_frontend_entry,
)


def _path_endswith(path: str, suffix: str) -> bool:
    return path.replace("\\", "/").endswith(suffix)


class TestFrontendEntryService(unittest.TestCase):
    def test_static_directories_return_only_when_present(self):
        with patch(
            "core.frontend_entry_service.os.path.exists",
            side_effect=lambda path: _path_endswith(path, "static"),
        ):
            self.assertEqual(get_legacy_static_dir("D:/app"), "D:/app\\static")
            self.assertIsNone(get_react_assets_dir("D:/app"))

        with patch(
            "core.frontend_entry_service.os.path.exists",
            side_effect=lambda path: _path_endswith(path, "static_react/assets"),
        ):
            self.assertIsNone(get_legacy_static_dir("D:/app"))
            self.assertEqual(get_react_assets_dir("D:/app"), "D:/app\\static_react\\assets")

    def test_resolve_frontend_entry_prefers_react_build(self):
        with (
            patch(
                "core.frontend_entry_service.os.path.exists",
                side_effect=lambda path: _path_endswith(path, "static_react/index.html"),
            ),
            patch("builtins.open", mock_open(read_data="<html>react</html>")),
        ):
            entry = resolve_frontend_entry("D:/app")

        self.assertEqual(entry.html, "<html>react</html>")
        self.assertIsNone(entry.fallback)

    def test_resolve_frontend_entry_falls_back_to_legacy_demo(self):
        with (
            patch(
                "core.frontend_entry_service.os.path.exists",
                side_effect=lambda path: _path_endswith(path, "frontend_demo.html"),
            ),
            patch("builtins.open", mock_open(read_data="<html>legacy</html>")),
        ):
            entry = resolve_frontend_entry("D:/app")

        self.assertEqual(entry.html, "<html>legacy</html>")
        self.assertIsNone(entry.fallback)

    def test_resolve_frontend_entry_returns_backend_status_when_no_page_exists(self):
        with patch("core.frontend_entry_service.os.path.exists", return_value=False):
            entry = resolve_frontend_entry("D:/app")

        self.assertIsNone(entry.html)
        self.assertEqual(entry.fallback, {"status": "ok", "message": "Backend is running."})


if __name__ == "__main__":
    unittest.main()
