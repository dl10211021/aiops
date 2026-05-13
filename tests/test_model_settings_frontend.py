from pathlib import Path


def test_config_center_exposes_model_settings_modal():
    app_source = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    config_source = Path("frontend/src/components/views/SystemConfigCenter.tsx").read_text(
        encoding="utf-8"
    )
    modal_source = Path("frontend/src/components/modals/ModelSettingsModal.tsx").read_text(
        encoding="utf-8"
    )

    assert "loadModelSettingsModal" in app_source
    assert "activeModal === 'model-settings'" in app_source
    assert "title: '模型配置'" in config_source
    assert "modal: 'model-settings'" in config_source
    assert "getProviders" in modal_source
    assert "getAssistantModelConfig" in modal_source
    assert "updateProviders" in modal_source
    assert "updateAssistantModelConfig" in modal_source
    assert "拉取模型" in modal_source
