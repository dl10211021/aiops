import unittest

from core.agent_sse import sse_event, sse_raw


class AgentSseTests(unittest.TestCase):
    def test_sse_event_uses_json_default_ascii_escaping(self):
        self.assertEqual(
            sse_event({"type": "status", "content": "思考中"}),
            'data: {"type": "status", "content": "\\u601d\\u8003\\u4e2d"}\n\n',
        )

    def test_sse_event_can_preserve_unicode(self):
        self.assertEqual(
            sse_event({"type": "status", "content": "思考中"}, ensure_ascii=False),
            'data: {"type": "status", "content": "思考中"}\n\n',
        )

    def test_sse_raw_wraps_already_serialized_payload(self):
        self.assertEqual(
            sse_raw('{"type":"done"}'),
            'data: {"type":"done"}\n\n',
        )


if __name__ == "__main__":
    unittest.main()
