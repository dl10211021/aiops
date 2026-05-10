import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core import app_config_service
from core.app_config_service import (
    AppConfigServiceError,
    build_llm_config_payload,
    get_session_retention_config_record,
    run_session_retention_policy_record,
    save_agent_runtime_config_record,
    save_embedding_config_record,
    save_session_retention_config_record,
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

    def test_session_retention_config_reads_file_values(self):
        env_path = self._env_path("retention_read")
        env_path.write_text(
            "OPSCORE_RETENTION_RAW_RESULT_DAYS=45\n"
            "OPSCORE_RETENTION_COMPRESSED_HISTORY_DAYS=200\n"
            "OPSCORE_RETENTION_AUDIT_METADATA_DAYS=400\n",
            encoding="utf-8",
        )

        config = get_session_retention_config_record(env={}, env_path=env_path)

        self.assertEqual(config["raw_result_days"], 45)
        self.assertEqual(config["compressed_history_days"], 200)
        self.assertEqual(config["audit_metadata_days"], 400)
        self.assertEqual(config["env_keys"]["raw_result_days"], "OPSCORE_RETENTION_RAW_RESULT_DAYS")

    def test_save_session_retention_config_persists_env_values(self):
        env_path = self._env_path("retention_save")
        with patch.object(
            app_config_service,
            "preview_session_retention_policy",
            return_value={"rows_scanned": 0, "rows_compacted": 0, "rows_deleted": 0},
        ):
            config = save_session_retention_config_record(
                enabled=True,
                raw_result_days=30,
                compressed_history_days=180,
                audit_metadata_days=365,
                max_result_chars=2500,
                preview_chars=1300,
                env_path=env_path,
            )

        content = env_path.read_text(encoding="utf-8")

        self.assertEqual(config["raw_result_days"], 30)
        self.assertIn("OPSCORE_SESSION_RETENTION_ENABLED=true", content)
        self.assertIn("OPSCORE_RETENTION_RAW_RESULT_DAYS=30", content)
        self.assertIn("OPSCORE_RETENTION_COMPRESSED_HISTORY_DAYS=180", content)
        self.assertIn("OPSCORE_RETENTION_AUDIT_METADATA_DAYS=365", content)

    def test_run_session_retention_policy_delegates_to_memory_db(self):
        fake_memory = Mock()
        fake_memory.apply_session_retention.return_value = {"rows_scanned": 1}

        with patch.dict("sys.modules", {"core.memory": Mock(memory_db=fake_memory)}):
            result = run_session_retention_policy_record()

        self.assertEqual(result, {"rows_scanned": 1})
        fake_memory.apply_session_retention.assert_called_once_with(dry_run=False)

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
