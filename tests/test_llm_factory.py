import unittest
import os
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from core.llm_factory import get_client_for_model

class TestLLMFactory(unittest.TestCase):
    def setUp(self):
        # We assume models.json exists and has gemini-2.5-flash and claude-3-7-sonnet-20250219
        os.environ["GOOGLE_API_KEY"] = "fake-google-key"
        os.environ["ANTHROPIC_API_KEY"] = "fake-anthropic-key"
        # Setup fallback
        os.environ["OPENAI_API_KEY"] = "fake-openai-key"

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
        # Using a model that doesn't have an env var required
        client, config = get_client_for_model("vllm-llama3")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(client.api_key, "dummy")

    def test_missing_model_fallback(self):
        client, config = get_client_for_model("unknown-model-123")
        self.assertIsInstance(client, AsyncOpenAI)
        self.assertEqual(config["protocol"], "openai")
        self.assertEqual(client.api_key, "fake-openai-key")

    def test_missing_api_key(self):
        # Unset the key explicitly
        del os.environ["GOOGLE_API_KEY"]
        with self.assertRaisesRegex(ValueError, "Missing API key"):
            get_client_for_model("gemini-2.5-flash")

if __name__ == '__main__':
    unittest.main()
