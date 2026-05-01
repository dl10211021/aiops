from __future__ import annotations

from typing import Any

from core.session_views import mask_sensitive_extra_args


def mask_asset_response(
    asset: dict[str, Any],
    sensitive_keys: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    safe_asset = dict(asset)
    if safe_asset.get("password"):
        safe_asset["password"] = "********"
    if isinstance(safe_asset.get("extra_args"), dict) and safe_asset["extra_args"]:
        safe_asset["extra_args"] = mask_sensitive_extra_args(safe_asset["extra_args"], sensitive_keys)
    return safe_asset


def mask_asset_responses(
    assets: list[dict[str, Any]],
    sensitive_keys: list[str] | tuple[str, ...],
) -> list[dict[str, Any]]:
    return [mask_asset_response(asset, sensitive_keys) for asset in assets]
