from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTTP_CLIENT = ROOT / "frontend" / "src" / "api" / "http.ts"


def test_structured_error_detail_preserves_error_type():
    source = HTTP_CLIENT.read_text(encoding="utf-8")

    assert "typeof value.error_type === 'string'" in source
    assert "? value.error_type" in source


def test_structured_error_detail_uses_message_classification():
    source = HTTP_CLIENT.read_text(encoding="utf-8")

    assert "const messageInferred = classifyErrorMessage(message)" in source
    assert "messageInferred.category" in source


def test_structured_error_detail_uses_error_code_classification():
    source = HTTP_CLIENT.read_text(encoding="utf-8")

    assert "function classifyErrorCode" in source
    assert "const codeInferred = classifyErrorCode(code)" in source
    assert "codeInferred.category || messageInferred.category" in source


def test_chinese_timeout_messages_are_classified_as_connection_errors():
    source = HTTP_CLIENT.read_text(encoding="utf-8")

    assert "message.includes('超时')" in source
    assert "message.includes('执行超过')" in source


def test_runtime_policy_error_categories_are_classified():
    source = HTTP_CLIENT.read_text(encoding="utf-8")

    assert "category: 'rate_limit'" in source
    assert "category: 'approval'" in source
    assert "category: 'policy'" in source
    assert "category: 'execution'" in source
