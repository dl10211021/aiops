import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import (
    DEFAULT_OPSCORE_HOST,
    DEFAULT_OPSCORE_PORT,
    SECURITY_HEADERS,
    app,
    get_log_level,
    get_runtime_host,
    get_runtime_port,
)


class TestProductionReadiness(unittest.TestCase):
    def test_healthz_returns_structured_status_without_auth(self):
        client = TestClient(app)
        response = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("checks", payload)
        self.assertIn("database", payload["checks"])
        self.assertIn("cron_store", payload["checks"])
        self.assertEqual(payload["checks"]["cron_store"]["status"], "ok")
        self.assertIn("storage", payload["checks"])
        self.assertIn("version", payload)

    def test_healthz_includes_baseline_security_headers(self):
        client = TestClient(app)
        response = client.get("/healthz")

        for header, value in SECURITY_HEADERS.items():
            self.assertEqual(response.headers[header], value)

    def test_env_example_documents_required_production_settings(self):
        env_example = Path(".env.example")
        self.assertTrue(env_example.exists(), ".env.example is required for production deployment")
        content = env_example.read_text(encoding="utf-8")

        for key in (
            "OPSCORE_API_TOKEN",
            "OPSCORE_ALLOWED_ORIGINS",
            "OPSCORE_HOST",
            "OPSCORE_PORT",
            "LOG_LEVEL",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
        ):
            self.assertIn(key, content)
        self.assertNotIn("gpustack_", content)

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

    def test_log_level_accepts_standard_names_only(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "debug"}, clear=True):
            self.assertEqual(get_log_level(), logging.DEBUG)

        with patch.dict("os.environ", {"LOG_LEVEL": "__dict__"}, clear=True):
            self.assertEqual(get_log_level(), logging.INFO)

    def test_docker_healthcheck_targets_healthz(self):
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("/healthz", dockerfile)

    def test_preflight_script_runs_required_quality_gates(self):
        preflight = Path("scripts/preflight.py").read_text(encoding="utf-8")

        for marker in (
            "backend unit tests",
            "python compile",
            "secret scan",
            "python dependency check",
            "frontend npm audit",
            "--audit-level=high",
            "frontend build",
        ):
            self.assertIn(marker, preflight)

    def test_root_readme_documents_onboarding_and_boundaries(self):
        readme = Path("README.md")
        self.assertTrue(readme.exists(), "README.md is required for agent and operator onboarding")
        content = readme.read_text(encoding="utf-8")

        for marker in (
            "python scripts/preflight.py --check-git",
            "http://localhost:8000",
            "/healthz",
            "docs/architecture/README.md",
            ".research/hermes-agent/",
            "worktree_audit.py --check-staged",
        ):
            self.assertIn(marker, content)

    def test_deployment_and_backup_docs_exist(self):
        for path in (
            Path("docs/deployment-production.md"),
            Path("docs/backup-restore.md"),
            Path("docs/release-checklist.md"),
        ):
            self.assertTrue(path.exists(), f"{path} is required")
            content = path.read_text(encoding="utf-8")
            self.assertIn("healthz", content)
            self.assertIn("rollback", content.lower())

    def test_github_actions_quality_gate_exists(self):
        workflow = Path(".github/workflows/ci.yml")
        self.assertTrue(workflow.exists(), "CI quality gate workflow is required")
        content = workflow.read_text(encoding="utf-8")
        ci_tests = Path("scripts/ci_backend_tests.py").read_text(encoding="utf-8")

        for marker in (
            "python scripts/ci_backend_tests.py",
            "python scripts/security_scan.py",
            "python -m pip check",
            "npm audit --audit-level=high",
            "npm run build",
        ):
            self.assertIn(marker, content)

        for marker in ("-W", "default", "unittest", "discover", "test*.py"):
            self.assertIn(marker, ci_tests)


if __name__ == "__main__":
    unittest.main()
