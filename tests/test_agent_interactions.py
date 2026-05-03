import asyncio
import json
import unittest

from core.agent_interactions import (
    _build_interaction_payload,
    _normalize_interaction_options,
    _wait_for_user_interaction,
)
from core.dispatcher import dispatcher


class TestAgentInteractions(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        dispatcher.pending_interactions.clear()

    def test_normalize_interaction_options_limits_and_coerces_items(self):
        options = _normalize_interaction_options(
            [
                {"label": "A" * 100, "value": "value-a", "description": "D" * 400},
                "直接输入",
                None,
            ]
        )

        self.assertEqual(len(options), 3)
        self.assertEqual(options[0]["label"], "A" * 80)
        self.assertEqual(options[0]["value"], "value-a")
        self.assertEqual(options[0]["description"], "D" * 300)
        self.assertEqual(options[1]["label"], "直接输入")
        self.assertEqual(options[2]["label"], "选项 3")

    def test_build_interaction_payload_clamps_timeout_and_choice_fallback(self):
        payload = _build_interaction_payload(
            "interaction-1",
            {
                "prompt": "选择方案",
                "input_type": "choice",
                "options": [],
                "timeout_seconds": 9999,
                "required": False,
            },
        )

        self.assertEqual(payload["type"], "user_interaction_request")
        self.assertEqual(payload["request_id"], "interaction-1")
        self.assertEqual(payload["input_type"], "text")
        self.assertEqual(payload["timeout_seconds"], 1800)
        self.assertFalse(payload["required"])

    async def test_wait_for_user_interaction_masks_password_in_safe_result(self):
        future = asyncio.get_running_loop().create_future()
        future.set_result({"value": "secret-value", "label": "root password"})
        dispatcher.pending_interactions["interaction-2"] = {"future": future}

        payload = {
            "input_type": "password",
            "timeout_seconds": 30,
        }
        tool_res, safe_tool_res = await _wait_for_user_interaction(
            "interaction-2",
            payload,
            future,
        )

        self.assertEqual(json.loads(tool_res)["value"], "secret-value")
        self.assertEqual(json.loads(safe_tool_res)["value"], "******")
        self.assertNotIn("interaction-2", dispatcher.pending_interactions)


if __name__ == "__main__":
    unittest.main()
