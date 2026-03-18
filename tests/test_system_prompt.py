import unittest
from unittest.mock import patch, MagicMock
from core.llm_execution import execute_chat_stream

class TestSystemPrompt(unittest.IsolatedAsyncioTestCase):
    @patch('core.llm_execution.get_client_for_model')
    async def test_anthropic_system_prompt(self, mock_get_client):
        mock_client = MagicMock()
        mock_config = {"protocol": "anthropic", "provider": "anthropic", "model": "claude"}
        mock_get_client.return_value = (mock_client, mock_config)

        mock_chunk = MagicMock()
        mock_chunk.type = "content_block_delta"
        mock_chunk.delta = MagicMock()
        mock_chunk.delta.type = "text_delta"
        mock_chunk.delta.text = "Hi"

        async def mock_stream():
            yield mock_chunk

        class MockCM:
            async def __aenter__(self):
                return mock_stream()
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_client.messages.stream.return_value = MockCM()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi"}
        ]
        
        results = []
        async for chunk in execute_chat_stream("claude", messages):
            results.append(chunk)

        mock_client.messages.stream.assert_called_once_with(
            model="claude",
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=8192
        )

if __name__ == '__main__':
    unittest.main()
