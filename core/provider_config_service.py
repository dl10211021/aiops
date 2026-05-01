from __future__ import annotations

import logging
from typing import Any

from core.llm_factory import get_all_providers, mask_provider_secrets, merge_provider_secrets, save_providers


logger = logging.getLogger(__name__)


class ProviderConfigServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def list_provider_config_records() -> list[dict[str, Any]]:
    return mask_provider_secrets(get_all_providers())


def save_provider_config_records(records: list[dict[str, Any]]) -> None:
    try:
        providers = merge_provider_secrets(records, get_all_providers())
        save_providers(providers)
    except Exception as exc:
        logger.error("保存模型供应商配置失败: %s", exc)
        raise ProviderConfigServiceError(500, f"保存供应商配置失败: {exc}") from exc
