import unittest
from unittest.mock import patch

from core import provider_config_service
from core.provider_config_service import (
    ProviderConfigServiceError,
    list_provider_config_records,
    save_provider_config_records,
)


class TestProviderConfigService(unittest.TestCase):
    def test_list_provider_configs_masks_secrets(self):
        providers = [{"id": "openai", "api_key": "secret", "base_url": "https://api.example/v1"}]

        with patch.object(provider_config_service, "get_all_providers", return_value=providers):
            result = list_provider_config_records()

        self.assertEqual(result[0]["api_key"], "********")

    def test_save_provider_configs_merges_existing_secrets(self):
        existing = [{"id": "openai", "api_key": "secret", "base_url": "https://old.example/v1"}]
        saved = {}

        def save(records):
            saved["records"] = records

        with (
            patch.object(provider_config_service, "get_all_providers", return_value=existing),
            patch.object(provider_config_service, "save_providers", side_effect=save),
        ):
            save_provider_config_records(
                [{"id": "openai", "api_key": "********", "base_url": "https://new.example/v1"}]
            )

        self.assertEqual(saved["records"][0]["api_key"], "secret")
        self.assertEqual(saved["records"][0]["base_url"], "https://new.example/v1")

    def test_save_provider_configs_maps_errors_to_500(self):
        with patch.object(provider_config_service, "save_providers", side_effect=RuntimeError("disk full")):
            with self.assertRaises(ProviderConfigServiceError) as ctx:
                save_provider_config_records([{"id": "openai"}])

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("disk full", ctx.exception.detail)
