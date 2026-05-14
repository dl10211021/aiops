from pathlib import Path


def test_connection_asset_catalog_exposes_common_and_full_directory_modes():
    selector_source = Path("frontend/src/components/modals/ConnectionAssetTypeSelector.tsx").read_text(
        encoding="utf-8"
    )
    model_source = Path("frontend/src/components/modals/connectionModalModel.ts").read_text(
        encoding="utf-8"
    )

    assert "assetCatalogMode" in selector_source
    assert "常用" in selector_source
    assert "完整目录" in selector_source
    assert "COMMON_ASSET_TYPE_IDS" in model_source
    assert "catalogModeSubTypeOptions" in model_source
    assert "'elastic_stack'" in model_source
    assert "'graylog'" in model_source
    assert "'loki'" in model_source


def test_connection_asset_catalog_exposes_logging_platform_category():
    catalog_source = Path("frontend/src/components/modals/connectionAssetCatalog.ts").read_text(
        encoding="utf-8"
    )
    display_source = Path("frontend/src/utils/assetDisplayMaps.ts").read_text(encoding="utf-8")
    hints_source = Path("frontend/src/components/modals/connectionHints.ts").read_text(
        encoding="utf-8"
    )

    assert "{ id: 'log', label: '日志平台', group: '平台工具' }" in catalog_source
    for asset_id in ("elastic_stack", "kibana", "elasticsearch", "logstash", "graylog", "loki", "opensearch"):
        assert f"id: '{asset_id}'" in catalog_source
    assert "log: '日志平台'" in display_source
    assert "log_api" in hints_source


def test_connection_http_params_exposes_managed_auth_and_custom_headers():
    params_source = Path("frontend/src/components/modals/ConnectionHttpParams.tsx").read_text(
        encoding="utf-8"
    )
    definitions_source = Path("frontend/src/components/modals/connectionParamDefinitions.ts").read_text(
        encoding="utf-8"
    )
    extension_source = Path("frontend/src/components/modals/ConnectionExtensionParam.tsx").read_text(
        encoding="utf-8"
    )

    assert "认证模式" in params_source
    assert "Basic Token" in params_source
    assert "自定义 Headers" in params_source
    assert "'auth_type'" in definitions_source
    assert "'custom_headers'" in definitions_source
    assert "Header-Name: value" in extension_source


def test_connection_asset_selector_supports_global_catalog_search():
    selector_source = Path("frontend/src/components/modals/ConnectionAssetTypeSelector.tsx").read_text(
        encoding="utf-8"
    )
    controller_source = Path("frontend/src/components/modals/useConnectionModalController.ts").read_text(
        encoding="utf-8"
    )
    model_source = Path("frontend/src/components/modals/connectionModalModel.ts").read_text(
        encoding="utf-8"
    )

    assert "全目录搜索" in selector_source
    assert "onAssetTypePick" in selector_source
    assert "globalSearchGroups" in selector_source
    assert "handleAssetTypePick" in controller_source
    assert "categorySummaries" in model_source
    assert "globalSearchOptions" in model_source
