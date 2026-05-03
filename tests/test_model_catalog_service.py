import asyncio
import unittest

from core.model_catalog_service import fetch_model_catalog


class TestModelCatalogService(unittest.TestCase):
    def test_fetch_model_catalog_uses_injected_fetcher(self):
        calls = []
        models = [{"id": "openai|gpt-4o", "name": "gpt-4o"}]

        async def fetcher(**kwargs):
            calls.append(kwargs)
            return models

        result = asyncio.run(
            fetch_model_catalog(
                provider_id="openai",
                refresh=True,
                fetcher=fetcher,
            )
        )

        self.assertEqual(result, models)
        self.assertEqual(calls, [{"provider_id": "openai", "refresh": True}])

    def test_fetch_model_catalog_uses_default_fetcher(self):
        from unittest.mock import patch

        models = [{"id": "default|model", "name": "model"}]

        async def fetcher(**_kwargs):
            return models

        with patch("core.model_catalog.get_available_models_for_provider", fetcher):
            result = asyncio.run(fetch_model_catalog())

        self.assertEqual(result, models)


if __name__ == "__main__":
    unittest.main()
