from __future__ import annotations

import asyncio
import logging


logger = logging.getLogger(__name__)

MODEL_FETCH_TIMEOUT_SECONDS = 12.0


async def get_available_models() -> list:
    return await get_available_models_for_provider()


async def get_available_models_for_provider(
    provider_id: str | None = None,
    refresh: bool = False,
) -> list:
    try:
        from core.llm_factory import get_all_providers
        from openai import AsyncOpenAI

        providers = get_all_providers()
        if provider_id:
            providers = [p for p in providers if p.get("id") == provider_id]

        async def fetch_provider_models(provider: dict) -> dict:
            provider_id_value = provider["id"]
            manual_models = [
                model.strip()
                for model in provider.get("models", "").split(",")
                if model.strip()
            ]
            models_list = [
                {"id": f"{provider_id_value}|{model}", "name": model}
                for model in manual_models
                if not refresh
            ]

            if refresh and provider.get("protocol") == "openai":
                try:
                    api_key = provider.get("api_key") or "dummy"
                    base_url = provider.get("base_url") or "https://api.openai.com/v1"
                    temp_client = AsyncOpenAI(
                        api_key=api_key,
                        base_url=base_url,
                        timeout=MODEL_FETCH_TIMEOUT_SECONDS,
                    )
                    response = await temp_client.models.list()
                    models_list = [
                        {"id": f"{provider_id_value}|{model.id}", "name": model.id}
                        for model in response.data
                    ]
                except Exception as exc:
                    logger.warning(
                        "Failed to fetch models for %s: %s",
                        provider.get("name"),
                        exc,
                    )
                    if manual_models:
                        models_list = [
                            {"id": f"{provider_id_value}|{model}", "name": model}
                            for model in manual_models
                        ]

            if not models_list:
                models_list.append(
                    {"id": f"{provider_id_value}|none", "name": "未获取到模型或配置错误"}
                )

            return {
                "provider_id": provider_id_value,
                "provider_name": provider["name"],
                "models": models_list,
            }

        return await asyncio.gather(*(fetch_provider_models(p) for p in providers))
    except Exception as exc:
        logger.error("Failed to fetch models: %s", exc)
        return []
