import json
import os


def test_models_config_structure():
    """
    Test that models.json exists, can be loaded, and contains
    the correct basic structure defined in the design document.
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models.json"
    )

    assert os.path.exists(config_path), f"models.json not found at {config_path}"

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "default_model" in config, "models.json is missing 'default_model' key"
    assert "models" in config, "models.json is missing 'models' key"
    assert isinstance(config["models"], dict), "'models' should be a dictionary"

    # Check that at least the default_model is defined in models
    default_model = config["default_model"]
    assert default_model in config["models"], (
        f"Default model '{default_model}' is not in 'models'"
    )

    # Check structure of a single model config
    model_config = config["models"][default_model]
    assert "provider" in model_config, "Model config is missing 'provider'"
    assert "protocol" in model_config, "Model config is missing 'protocol'"
    assert "api_key_env" in model_config, "Model config is missing 'api_key_env'"
    assert "supports_thinking" in model_config, (
        "Model config is missing 'supports_thinking'"
    )
    assert isinstance(model_config["supports_thinking"], bool), (
        "'supports_thinking' must be a boolean"
    )


if __name__ == "__main__":
    test_models_config_structure()
    print("All tests passed.")
