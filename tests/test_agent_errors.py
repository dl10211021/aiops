import unittest

from core.agent_errors import build_agent_loop_error_payload


class AgentErrorPayloadTests(unittest.TestCase):
    def test_timeout_errors_get_friendly_connectivity_message(self):
        payload = build_agent_loop_error_payload("request timeout")

        self.assertEqual(payload["type"], "error")
        self.assertIn("无法连接到 AI 模型接口", payload["content"])
        self.assertIn("模型服务地址不可达", payload["content"])

    def test_connect_errors_get_friendly_connectivity_message(self):
        payload = build_agent_loop_error_payload("connect failed")

        self.assertEqual(payload["type"], "error")
        self.assertIn("API Key 或模型名称配置不正确", payload["content"])

    def test_generic_errors_keep_detail_for_debugging(self):
        payload = build_agent_loop_error_payload("provider rejected request")

        self.assertEqual(payload["type"], "error")
        self.assertEqual(
            payload["content"],
            "❌ AI 思考时发生异常，请稍后再试。详细信息：`provider rejected request`",
        )


if __name__ == "__main__":
    unittest.main()
