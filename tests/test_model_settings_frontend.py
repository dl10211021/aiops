from pathlib import Path


def test_config_center_exposes_model_settings_modal():
    app_source = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    config_source = Path("frontend/src/components/views/SystemConfigCenter.tsx").read_text(
        encoding="utf-8"
    )
    modal_source = Path("frontend/src/components/modals/LLMConfigModal.tsx").read_text(
        encoding="utf-8"
    )
    assistant_source = Path("frontend/src/components/modals/LLMAssistantModelPanel.tsx").read_text(
        encoding="utf-8"
    )
    runtime_source = Path("frontend/src/components/modals/LLMRuntimeConfigPanel.tsx").read_text(
        encoding="utf-8"
    )

    assert "loadLLMConfigModal" in app_source
    assert "activeModal === 'llm-config'" in app_source
    assert "title: '模型配置'" in config_source
    assert "modal: 'llm-config'" in config_source
    assert "主模型 / 辅助模型" in config_source
    assert "模型配置 · 主模型 / 辅助模型" in modal_source
    assert "供应商连接参数" in modal_source
    assert "测试当前供应商并获取模型" in modal_source
    assert "主模型 / 辅助思维模型" in assistant_source
    assert "辅助思维模型负责画像、记忆压缩、思维链审查和成功经验沉淀" in assistant_source
    assert "Agent 执行保护" in runtime_source
