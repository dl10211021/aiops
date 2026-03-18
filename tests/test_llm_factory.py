import unittest
import os
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from core.llm_factory import get_client_for_model, DEFAULT_PROVIDERS, save_providers

class TestLLMFactory(unittest.TestCase):
    def setUp(self):
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
        save_providers(mock_providers)

    def test_openai_protocol(self):
        client, config = get_client_for_model("gemini-2.5-flash")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["protocol"], "openai")
        self.assertEqual(client.api_key, "fake-google-key")

    def test_anthropic_protocol(self):
        client, config = get_client_for_model("claude-3-7-sonnet-20250219")
        self.assertIsInstance(client, AsyncAnthropic)
        self.assertEqual(config["protocol"], "anthropic")
        self.assertEqual(client.api_key, "fake-anthropic-key")

    def test_local_protocol_no_key(self):
        client, config = get_client_for_model("vllm-llama3")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(client.api_key, "dummy")

    def test_missing_model_fallback(self):
        # Falls back to the first provider (google)
        client, config = get_client_for_model("unknown-model-123")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["protocol"], "openai")
        self.assertEqual(client.api_key, "fake-google-key")

if __name__ == '__main__':
    unittest.main()
