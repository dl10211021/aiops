import unittest

from core.agent_headless_setup import prepare_headless_agent_run


class FakeDispatcher:
    def __init__(self):
        self.skill_path_requests = []
        self.tool_contexts = []

    def get_active_skill_paths(self, active_skills):
        self.skill_path_requests.append(active_skills)
        return [f"D:/skills/{name}" for name in active_skills]

    def get_available_tools(self, context):
        self.tool_contexts.append(context)
        return [{"name": "run"}]


class AgentHeadlessSetupTests(unittest.TestCase):
    def test_prepares_headless_prompt_context_tools_and_permission_inheritance(self):
        dispatcher = FakeDispatcher()
        active_sessions = {
            "sid-1": {
                "info": {
                    "asset_type": "virtual",
                    "protocol": "virtual",
                    "host": "workspace",
                    "active_skills": ["skill-creator"],
                    "allow_modifications": True,
                    "agent_profile": "ops",
                }
            }
        }

        run = prepare_headless_agent_run(
            session_id="sid-1",
            task_description="检查技能工程",
            inherited_allow_mod=True,
            model_name=None,
            active_sessions=active_sessions,
            dispatcher=dispatcher,
            default_model_resolver=lambda: "default-model",
            model_client_resolver=lambda model: (f"client:{model}", None),
            profile_loader=lambda profile: f"BASE:{profile}",
        )

        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(run.model_name, "default-model")
        self.assertEqual(run.agent_profile, "ops")
        self.assertEqual(run.host, "workspace")
        self.assertTrue(run.context["allow_modifications"])
        self.assertEqual(run.context["execution_mode"], "headless")
        self.assertEqual(run.context["trigger_source"], "background_agent")
        self.assertEqual(run.context["active_skill_paths"], ["D:/skills/skill-creator"])
        self.assertEqual(run.tools, [{"name": "run"}])
        self.assertIn("BASE:ops", run.messages[0]["content"])
        self.assertIn("检查技能工程", run.messages[0]["content"])
        self.assertEqual(run.messages[1], {"role": "user", "content": "请开始执行任务。"})
        self.assertEqual(dispatcher.skill_path_requests, [["skill-creator"]])
        self.assertEqual(dispatcher.tool_contexts, [run.context])

    def test_denies_modifications_when_parent_does_not_allow(self):
        run = prepare_headless_agent_run(
            session_id="sid-1",
            task_description="巡检",
            inherited_allow_mod=False,
            model_name="chosen",
            active_sessions={
                "sid-1": {"info": {"host": "10.0.0.1", "allow_modifications": True}}
            },
            dispatcher=FakeDispatcher(),
            default_model_resolver=lambda: "default",
            model_client_resolver=lambda model: (object(), None),
            profile_loader=lambda profile: f"BASE:{profile}",
        )

        self.assertIsNotNone(run)
        assert run is not None
        self.assertFalse(run.context["allow_modifications"])

    def test_validates_model_before_returning_offline_session(self):
        calls = []

        run = prepare_headless_agent_run(
            session_id="missing",
            task_description="巡检",
            inherited_allow_mod=False,
            model_name=None,
            active_sessions={},
            dispatcher=FakeDispatcher(),
            default_model_resolver=lambda: "default-model",
            model_client_resolver=lambda model: calls.append(model) or (object(), None),
            profile_loader=lambda profile: f"BASE:{profile}",
        )

        self.assertIsNone(run)
        self.assertEqual(calls, ["default-model"])


if __name__ == "__main__":
    unittest.main()
