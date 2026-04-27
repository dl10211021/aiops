import unittest
from pathlib import Path
from unittest.mock import patch
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from core import llm_factory

class TestLLMFactory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path.cwd() / "tests" / "tmp_llm_factory"
        self.tmpdir.mkdir(parents=True, exist_ok=True)
        self.provider_path = self.tmpdir / "providers.json"
        self.provider_path_patcher = patch.object(
            llm_factory, "PROVIDERS_JSON_PATH", self.provider_path
        )
        self.provider_path_patcher.start()
        # Setup specific mock providers
        mock_providers = [
            {
                "id": "google",
                "name": "Google",
                "protocol": "openai",
                "api_key": "fake-google-key",
                "models": "gemini-2.5-flash"
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "protocol": "anthropic",
                "api_key": "fake-anthropic-key",
                "models": "claude-3-7-sonnet-20250219"
            },
            {
                "id": "ollama",
                "name": "Ollama",
                "protocol": "openai",
                "api_key": "dummy",
                "models": "vllm-llama3"
            }
        ]
        llm_factory.save_providers(mock_providers)

    def tearDown(self):
        self.provider_path_patcher.stop()
        if self.provider_path.exists():
            self.provider_path.unlink()
        if self.tmpdir.exists():
            self.tmpdir.rmdir()

    def test_openai_protocol(self):
        client, config = llm_factory.get_client_for_model("gemini-2.5-flash")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["protocol"], "openai")
        self.assertEqual(client.api_key, "fake-google-key")

    def test_anthropic_protocol(self):
        client, config = llm_factory.get_client_for_model("claude-3-7-sonnet-20250219")
        self.assertIsInstance(client, AsyncAnthropic)
        self.assertEqual(config["protocol"], "anthropic")
        self.assertEqual(client.api_key, "fake-anthropic-key")

    def test_local_protocol_no_key(self):
        client, config = llm_factory.get_client_for_model("vllm-llama3")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(client.api_key, "dummy")

    def test_missing_model_fallback(self):
        # Falls back to the first provider (google)
        client, config = llm_factory.get_client_for_model("unknown-model-123")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["protocol"], "openai")
        self.assertEqual(client.api_key, "fake-google-key")

    def test_default_model_id_uses_first_configured_provider_model(self):
        self.assertEqual(llm_factory.get_default_model_id(), "google|gemini-2.5-flash")

if __name__ == '__main__':
    unittest.main()
