import unittest
from unittest.mock import Mock, patch

from core.health_service import build_health_status


def _hydrate_status():
    return {"total": 2, "done": 1, "success": 1, "running": True}


def _path_endswith(path: str, suffix: str) -> bool:
    return path.replace("\\", "/").endswith(suffix)


class TestHealthService(unittest.TestCase):
    def test_build_health_status_reports_ok_when_core_checks_pass(self):
        connection = Mock()
        with (
            patch(
                "core.health_service.os.path.exists",
                side_effect=lambda path: _path_endswith(path, "static_react/index.html"),
            ),
            patch("core.health_service.os.access", return_value=True),
            patch("core.health_service.sqlite3.connect", return_value=connection),
        ):
            payload = build_health_status(
                base_path="D:/app",
                root_dir="D:/app",
                version="1.0",
                hydrate_status_getter=_hydrate_status,
            )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "opscore-aiops")
        self.assertEqual(payload["version"], "1.0")
        self.assertEqual(payload["checks"]["frontend"]["status"], "ok")
        self.assertEqual(payload["checks"]["cron_store"]["message"], "not initialized")
        self.assertEqual(payload["checks"]["hydrate"], _hydrate_status())

    def test_missing_frontend_build_marks_overall_status_warning(self):
        connection = Mock()
        with (
            patch("core.health_service.os.path.exists", return_value=False),
            patch("core.health_service.os.access", return_value=True),
            patch("core.health_service.sqlite3.connect", return_value=connection),
        ):
            payload = build_health_status(
                base_path="D:/app",
                root_dir="D:/app",
                version="1.0",
                hydrate_status_getter=_hydrate_status,
            )

        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["checks"]["frontend"]["status"], "warning")

    def test_database_failure_marks_overall_status_error(self):
        with (
            patch(
                "core.health_service.os.path.exists",
                side_effect=lambda path: _path_endswith(path, "static_react/index.html"),
            ),
            patch("core.health_service.os.access", return_value=True),
            patch("core.health_service.sqlite3.connect", side_effect=RuntimeError("disk unavailable")),
        ):
            payload = build_health_status(
                base_path="D:/app",
                root_dir="D:/app",
                version="1.0",
                hydrate_status_getter=_hydrate_status,
            )

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["checks"]["database"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
