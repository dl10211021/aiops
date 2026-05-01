import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import app_config_service
from core.app_config_service import (
    AppConfigServiceError,
    build_llm_config_payload,
    save_agent_runtime_config_record,
    save_embedding_config_record,
    update_env_file_values,
)


class TestAppConfigService(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_app_config_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _env_path(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_app_config_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root / ".env"

    def test_update_env_file_values_replaces_existing_keys(self):
        env_path = self._env_path("update")
        env_path.write_text("A=1\nB=2\n", encoding="utf-8")

        update_env_file_values({"B": "updated", "C": "3"}, env_path)

        self.assertEqual(env_path.read_text(encoding="utf-8"), "A=1\nB=updated\nC=3\n")

    def test_build_llm_config_prefers_runtime_env_and_masks_key(self):
        env_path = self._env_path("llm")
        env_path.write_text("OPENAI_BASE_URL=https://file.example/v1\nOPENAI_API_KEY=file-secret\n", encoding="utf-8")

        payload = build_llm_config_payload(
            {"OPENAI_BASE_URL": "https://runtime.example/v1", "OPENAI_API_KEY": "runtime-secret"},
            env_path,
        )

        self.assertEqual(payload["base_url"], "https://runtime.example/v1")
        self.assertEqual(payload["api_key"], "********")

    def test_save_agent_runtime_config_persists_step_limits(self):
        env_path = self._env_path("agent")
        with patch.object(
            app_config_service,
            "update_agent_runtime_config",
            return_value={"chat_max_steps": 90, "headless_max_steps": 70},
        ):
            config = save_agent_runtime_config_record(90, 70, env_path)

        content = env_path.read_text(encoding="utf-8")

        self.assertEqual(config["chat_max_steps"], 90)
        self.assertIn("OPSCORE_AGENT_MAX_STEPS=90", content)
        self.assertIn("OPSCORE_HEADLESS_AGENT_MAX_STEPS=70", content)

    def test_save_embedding_config_persists_model_and_dim(self):
        env_path = self._env_path("embedding")
        with patch.object(app_config_service, "update_embedding_config") as update:
            save_embedding_config_record("text-embedding", 1024, env_path)

        content = env_path.read_text(encoding="utf-8")

        update.assert_called_once_with("text-embedding", 1024)
        self.assertIn("EMBEDDING_MODEL=text-embedding", content)
        self.assertIn("EMBEDDING_DIM=1024", content)

    def test_save_embedding_config_maps_errors_to_500(self):
        with patch.object(app_config_service, "update_embedding_config", side_effect=RuntimeError("bad dim")):
            with self.assertRaises(AppConfigServiceError) as ctx:
                save_embedding_config_record("bad", 0)

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "bad dim")
