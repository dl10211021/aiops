import os
import unittest
from unittest.mock import patch

from core.agent_runtime_config import (
    agent_max_steps,
    agent_step_limit_instruction,
    get_agent_runtime_config,
    update_agent_runtime_config,
)


class TestAgentRuntimeConfig(unittest.TestCase):
    def test_agent_max_steps_defaults_and_bounds(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(agent_max_steps("chat"), 80)
            self.assertEqual(agent_max_steps("headless"), 60)

        with patch.dict("os.environ", {"OPSCORE_AGENT_MAX_STEPS": "5"}, clear=True):
            self.assertEqual(agent_max_steps("chat"), 10)

        with patch.dict("os.environ", {"OPSCORE_AGENT_MAX_STEPS": "999"}, clear=True):
            self.assertEqual(agent_max_steps("chat"), 200)

        with patch.dict("os.environ", {"OPSCORE_AGENT_MAX_STEPS": "abc"}, clear=True):
            self.assertEqual(agent_max_steps("chat"), 80)

        with patch.dict(
            "os.environ",
            {
                "OPSCORE_AGENT_MAX_STEPS": "90",
                "OPSCORE_HEADLESS_AGENT_MAX_STEPS": "70",
            },
            clear=True,
        ):
            self.assertEqual(agent_max_steps("headless"), 70)

    def test_update_agent_runtime_config_clamps_and_updates_environment(self):
        with patch.dict("os.environ", {}, clear=True):
            config = update_agent_runtime_config(999, 1)

            self.assertEqual(config["chat_max_steps"], 200)
            self.assertEqual(config["headless_max_steps"], 10)
            self.assertEqual(config["min_steps"], 10)
            self.assertEqual(config["max_steps"], 200)
            self.assertEqual("200", os.environ["OPSCORE_AGENT_MAX_STEPS"])
            self.assertEqual("10", os.environ["OPSCORE_HEADLESS_AGENT_MAX_STEPS"])

    def test_get_agent_runtime_config_exposes_defaults_and_env_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            config = get_agent_runtime_config()

        self.assertEqual(
            config["defaults"],
            {"chat_max_steps": 80, "headless_max_steps": 60},
        )
        self.assertEqual(
            config["env_keys"],
            {
                "chat_max_steps": "OPSCORE_AGENT_MAX_STEPS",
                "headless_max_steps": "OPSCORE_HEADLESS_AGENT_MAX_STEPS",
            },
        )

    def test_agent_step_limit_instruction_forces_summary_without_tools(self):
        instruction = agent_step_limit_instruction(80)

        self.assertIn("80 步执行保护上限", instruction)
        self.assertIn("停止继续调用任何工具", instruction)
        self.assertIn("阶段性运维报告", instruction)
        self.assertIn("未完成项目", instruction)


if __name__ == "__main__":
    unittest.main()
