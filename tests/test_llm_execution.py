import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm_execution import execute_chat_stream


class TestLLMExecution(unittest.IsolatedAsyncioTestCase):
    @patch("core.llm_execution.get_client_for_model")
    async def test_openai_standard(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_config = {"protocol": "openai", "provider": "openai", "model": "gpt-4o"}
        mock_get_client.return_value = (mock_client, mock_config)

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.choices[0].delta.reasoning_content = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = " World"
        mock_chunk2.choices[0].delta.reasoning_content = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_client.chat.completions.create.return_value = mock_stream()

        messages = [{"role": "user", "content": "Hi"}]
        results = []
        async for chunk in execute_chat_stream("gpt-4o", messages):
            results.append(chunk)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"type": "content", "content": "Hello"})
        self.assertEqual(results[1], {"type": "content", "content": " World"})

        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o", messages=messages, stream=True
        )

    @patch("core.llm_execution.get_client_for_model")
    async def test_openai_reasoning(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_config = {"protocol": "openai", "provider": "openai", "model": "o3-mini"}
        mock_get_client.return_value = (mock_client, mock_config)

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = None
        mock_chunk1.choices[0].delta.reasoning_content = "Thinking..."

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = " Done"
        mock_chunk2.choices[0].delta.reasoning_content = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        mock_client.chat.completions.create.return_value = mock_stream()

        messages = [{"role": "user", "content": "Hi"}]
        results = []
        async for chunk in execute_chat_stream(
            "o3-mini", messages, thinking_mode="high"
        ):
            results.append(chunk)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"type": "thinking", "content": "Thinking..."})
        self.assertEqual(results[1], {"type": "content", "content": " Done"})

        mock_client.chat.completions.create.assert_called_once_with(
            model="o3-mini", messages=messages, stream=True, reasoning_effort="high"
        )

    @patch("core.llm_execution.get_client_for_model")
    async def test_anthropic_standard(self, mock_get_client):
        mock_client = MagicMock()
        mock_config = {
            "protocol": "anthropic",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet-20250219",
        }
        mock_get_client.return_value = (mock_client, mock_config)

        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_delta"
        mock_chunk1.delta = MagicMock()
        mock_chunk1.delta.type = "text_delta"
        mock_chunk1.delta.text = "Hello"

        async def mock_stream():
            yield mock_chunk1

        class MockCM:
            async def __aenter__(self):
                return mock_stream()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_client.messages.stream.return_value = MockCM()

        messages = [{"role": "user", "content": "Hi"}]
        results = []
        async for chunk in execute_chat_stream("claude-3-7-sonnet-20250219", messages):
            results.append(chunk)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"type": "content", "content": "Hello"})

        mock_client.messages.stream.assert_called_once_with(
            model="claude-3-7-sonnet-20250219", messages=messages, max_tokens=8192
        )

    @patch("core.llm_execution.get_client_for_model")
    async def test_anthropic_thinking(self, mock_get_client):
        mock_client = MagicMock()
        mock_config = {
            "protocol": "anthropic",
            "provider": "anthropic",
            "model": "claude-3-7-sonnet-20250219",
            "supports_thinking": True,
        }
        mock_get_client.return_value = (mock_client, mock_config)

        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_delta"
        mock_chunk1.delta = MagicMock()
        mock_chunk1.delta.type = "thinking_delta"
        mock_chunk1.delta.thinking = "Hm..."

        mock_chunk2 = MagicMock()
        mock_chunk2.type = "content_block_delta"
        mock_chunk2.delta = MagicMock()
        mock_chunk2.delta.type = "text_delta"
        mock_chunk2.delta.text = " Yes"

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        class MockCM:
            async def __aenter__(self):
                return mock_stream()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_client.messages.stream.return_value = MockCM()

        messages = [{"role": "user", "content": "Hi"}]
        results = []
        async for chunk in execute_chat_stream(
            "claude-3-7-sonnet-20250219", messages, thinking_mode="low"
        ):
            results.append(chunk)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"type": "thinking", "content": "Hm..."})
        self.assertEqual(results[1], {"type": "content", "content": " Yes"})

        mock_client.messages.stream.assert_called_once_with(
            model="claude-3-7-sonnet-20250219",
            messages=messages,
            max_tokens=8192,
            thinking={"type": "enabled", "budget_tokens": 1024},
            temperature=1.0,
        )


if __name__ == "__main__":
    unittest.main()
