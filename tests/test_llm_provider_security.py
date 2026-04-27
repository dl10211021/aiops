import unittest

from core.llm_factory import mask_provider_secrets, merge_provider_secrets


class TestLLMProviderSecurity(unittest.TestCase):
    def test_masks_provider_api_keys_for_responses(self):
        providers = [{"id": "p1", "api_key": "real-key"}]

        masked = mask_provider_secrets(providers)

        self.assertEqual(masked[0]["api_key"], "********")
        self.assertEqual(providers[0]["api_key"], "real-key")

    def test_merge_preserves_existing_key_when_placeholder_submitted(self):
        existing = [{"id": "p1", "api_key": "real-key", "name": "old"}]
        incoming = [{"id": "p1", "api_key": "********", "name": "new"}]

        merged = merge_provider_secrets(incoming, existing)

        self.assertEqual(merged[0]["api_key"], "real-key")
        self.assertEqual(merged[0]["name"], "new")


if __name__ == "__main__":
    unittest.main()
