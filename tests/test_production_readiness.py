import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


class TestProductionReadiness(unittest.TestCase):
    def test_healthz_returns_structured_status_without_auth(self):
        client = TestClient(app)
        response = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("checks", payload)
        self.assertIn("database", payload["checks"])
        self.assertIn("storage", payload["checks"])
        self.assertIn("version", payload)

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
            "frontend build",
        ):
            self.assertIn(marker, preflight)

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

        for marker in (
            "python -W default -m unittest discover",
            "python scripts/security_scan.py",
            "python -m pip check",
            "npm run build",
        ):
            self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
