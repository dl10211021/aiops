import os
import unittest
from unittest.mock import patch
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from core.llm_factory import get_client_for_model


class TestLLMFactory(unittest.TestCase):
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_google_key"})
    def test_openai_protocol_with_env_var(self):
        client, config = get_client_for_model("gemini-2.5-flash")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["provider"], "google")
        self.assertEqual(client.api_key, "test_google_key")
        self.assertEqual(
            str(client.base_url),
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_anthropic_key"})
    def test_anthropic_protocol(self):
        client, config = get_client_for_model("claude-3-7-sonnet-20250219")
        self.assertIsInstance(client, AsyncAnthropic)
        self.assertEqual(config["provider"], "anthropic")
        self.assertEqual(client.api_key, "test_anthropic_key")

    def test_local_provider_no_env_var(self):
        client, config = get_client_for_model("ollama-deepseek-r1")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["provider"], "local")
        self.assertEqual(client.api_key, "dummy")
        self.assertEqual(str(client.base_url), "http://localhost:11434/v1/")

    def test_missing_model(self):
        with self.assertRaisesRegex(ValueError, "not found in models.json"):
            get_client_for_model("nonexistent-model")

    @patch.dict(os.environ, clear=True)
    def test_missing_env_var(self):
        with self.assertRaisesRegex(
            ValueError, "Missing API key: Environment variable"
        ):
            get_client_for_model("gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
