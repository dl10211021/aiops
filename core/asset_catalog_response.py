from __future__ import annotations

from core.asset_capabilities import category_metadata, connector_metadata
from core.asset_protocols import get_asset_catalog


def build_asset_types_response(types: list[dict] | None = None) -> dict:
    asset_types = types if types is not None else get_asset_catalog()
    categories = []
    connector_groups = []
    seen_categories = set()
    seen_connectors = set()
    for item in asset_types:
        category = item.get("category") or "other"
        if category not in seen_categories:
            seen_categories.add(category)
            categories.append(category_metadata(category))
        connector = ((item.get("capability") or {}).get("connector")) or "unknown"
        if connector not in seen_connectors:
            seen_connectors.add(connector)
            connector_groups.append(connector_metadata(connector))
    categories.sort(key=lambda item: (item.get("order", 999), item.get("label", "")))
    connector_groups.sort(key=lambda item: (item.get("order", 999), item.get("label", "")))
    return {
        "types": asset_types,
        "categories": categories,
        "connector_groups": connector_groups,
    }
