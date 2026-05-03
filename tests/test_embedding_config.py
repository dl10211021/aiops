import sys
import types
import unittest
from pathlib import Path

from core import embedding_config


class TestEmbeddingConfig(unittest.TestCase):
    def setUp(self):
        self.original_config = embedding_config.get_embedding_config()

    def tearDown(self):
        embedding_config.update_embedding_config(*self.original_config)

    def test_update_embedding_config_updates_current_values_and_logs(self):
        with self.assertLogs("core.embedding_config", level="INFO") as logs:
            embedding_config.update_embedding_config("text-embedding-test", 1024)

        self.assertEqual(
            embedding_config.get_embedding_config(),
            ("text-embedding-test", 1024),
        )
        self.assertTrue(
            any(
                "Embedding config updated: model=text-embedding-test, dim=1024" in item
                for item in logs.output
            )
        )

    def test_update_embedding_config_syncs_agent_compat_globals(self):
        previous_agent_module = sys.modules.get("core.agent")
        fake_agent_module = types.ModuleType("core.agent")

        try:
            sys.modules["core.agent"] = fake_agent_module
            embedding_config.update_embedding_config("compat-embedding-test", 1536)

            self.assertEqual(fake_agent_module.EMBEDDING_MODEL, "compat-embedding-test")
            self.assertEqual(fake_agent_module.EMBEDDING_DIM, 1536)
        finally:
            if previous_agent_module is None:
                sys.modules.pop("core.agent", None)
            else:
                sys.modules["core.agent"] = previous_agent_module

    def test_consumers_read_embedding_config_without_agent_dependency(self):
        for path in (
            Path("core/app_config_service.py"),
            Path("core/memory.py"),
            Path("core/rag.py"),
        ):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("from core.agent import EMBEDDING_MODEL", content)
            self.assertNotIn("from core.agent import EMBEDDING_DIM", content)


if __name__ == "__main__":
    unittest.main()
