import json
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from core import llm_factory


class TestLLMProviderConfig(unittest.TestCase):
    def test_normalize_provider_config_accepts_partial_custom_openai_provider(self):
        provider = llm_factory.normalize_provider_config(
            {
                "id": " custom gpu ",
                "name": "",
                "protocol": "custom",
                "base_url": " http://192.168.127.8/v1 ",
                "api_key": " key ",
            }
        )

        self.assertEqual(provider["id"], "custom_gpu")
        self.assertEqual(provider["name"], "custom_gpu")
        self.assertEqual(provider["protocol"], "openai")
        self.assertEqual(provider["base_url"], "http://192.168.127.8/v1")
        self.assertEqual(provider["api_key"], "key")
        self.assertEqual(provider["models"], "")

    def test_merge_provider_secrets_preserves_masked_api_key(self):
        merged = llm_factory.merge_provider_secrets(
            [
                {
                    "id": "gpu",
                    "name": "GPU",
                    "protocol": "openai",
                    "base_url": "http://gpu/v1",
                    "api_key": "********",
                    "models": "",
                }
            ],
            [
                {
                    "id": "gpu",
                    "name": "GPU",
                    "protocol": "openai",
                    "base_url": "http://old/v1",
                    "api_key": "secret",
                    "models": "",
                }
            ],
        )

        self.assertEqual(merged[0]["api_key"], "secret")
        self.assertEqual(merged[0]["base_url"], "http://gpu/v1")

    def test_save_providers_writes_normalized_json_atomically(self):
        tmpdir = Path.cwd() / "tests" / "tmp_provider_config"
        tmpdir.mkdir(parents=True, exist_ok=True)
        path = tmpdir / "providers.json"
        try:
            with patch.object(llm_factory, "PROVIDERS_JSON_PATH", path):
                llm_factory.save_providers(
                    [
                        {
                            "id": " custom gpu ",
                            "name": "GPUStack",
                            "protocol": "custom",
                            "base_url": " http://gpu/v1 ",
                            "api_key": "secret",
                        }
                    ]
                )

                saved = json.loads(path.read_text(encoding="utf-8"))
        finally:
            if path.exists():
                path.unlink()
            if tmpdir.exists():
                tmpdir.rmdir()

        self.assertEqual(saved[0]["id"], "custom_gpu")
        self.assertEqual(saved[0]["protocol"], "openai")
        self.assertEqual(saved[0]["models"], "")

    def test_refresh_models_fetches_remote_even_when_manual_models_exist(self):
        from core import model_catalog

        class FakeModel:
            def __init__(self, model_id):
                self.id = model_id

        class FakeModels:
            async def list(self):
                return type("Response", (), {"data": [FakeModel("qwen3.6-35b-a3b-awq")]})()

        class FakeOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.models = FakeModels()

        providers = [
            {
                "id": "gpu",
                "name": "GPUStack",
                "protocol": "openai",
                "base_url": "http://192.168.127.8/v1",
                "api_key": "secret",
                "models": "old-manual-model",
            }
        ]

        with (
            patch("core.llm_factory.get_all_providers", return_value=providers),
            patch("openai.AsyncOpenAI", FakeOpenAI),
        ):
            result = asyncio.run(
                model_catalog.get_available_models_for_provider(
                    provider_id="gpu",
                    refresh=True,
                )
            )

        names = [model["name"] for model in result[0]["models"]]
        self.assertEqual(names, ["qwen3.6-35b-a3b-awq"])

    def test_models_without_refresh_do_not_fetch_remote_when_manual_models_missing(self):
        from core import model_catalog

        class UnexpectedOpenAI:
            def __init__(self, **kwargs):
                raise AssertionError("model catalog should not call remote discovery")

        providers = [
            {
                "id": "gpu",
                "name": "GPUStack",
                "protocol": "openai",
                "base_url": "http://192.168.127.8/v1",
                "api_key": "secret",
                "models": "",
            }
        ]

        with (
            patch("core.llm_factory.get_all_providers", return_value=providers),
            patch("openai.AsyncOpenAI", UnexpectedOpenAI),
        ):
            result = asyncio.run(
                model_catalog.get_available_models_for_provider(
                    provider_id="gpu",
                    refresh=False,
                )
            )

        self.assertEqual(
            result[0]["models"],
            [{"id": "gpu|none", "name": "未获取到模型或配置错误"}],
        )


if __name__ == "__main__":
    unittest.main()
