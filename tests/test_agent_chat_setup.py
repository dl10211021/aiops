import unittest
from unittest.mock import patch

from core.agent_chat_setup import prepare_chat_agent_run


class FakeMemoryStore:
    def __init__(self):
        self.messages = [{"role": "assistant", "content": "历史"}]
        self.appended = []
        self.ltm_calls = []
        self.asset_profile = None
        self.asset_profile_for_context = None
        self.asset_profile_context_calls = []

    def get_messages(self, session_id):
        self.read_session_id = session_id
        return self.messages

    def append_message(self, session_id, message):
        self.appended.append((session_id, message))

    async def retrieve_ltm(
        self,
        session_id,
        user_message,
        emb_client,
        embedding_model,
        memory_scope_ids=None,
    ):
        self.ltm_calls.append(
            (session_id, user_message, emb_client, embedding_model, memory_scope_ids)
        )
        return "LTM-CONTEXT"

    async def retrieve_ltm_with_references(
        self,
        session_id,
        user_message,
        emb_client,
        embedding_model,
        memory_scope_ids=None,
    ):
        context = await self.retrieve_ltm(
            session_id,
            user_message,
            emb_client,
            embedding_model,
            memory_scope_ids=memory_scope_ids,
        )
        return context, [{"scope_id": "sid-1", "summary_preview": "LTM-CONTEXT"}]

    def get_asset_profile(self, session_id):
        self.asset_profile_session_id = session_id
        return self.asset_profile

    def get_asset_profile_for_session_context(self, session_id, asset_key, host):
        self.asset_profile_context_calls.append((session_id, asset_key, host))
        return self.asset_profile_for_context


class FakeDispatcher:
    def __init__(self):
        self.skill_path_requests = []
        self.instruction_requests = []
        self.tool_contexts = []

    def get_active_skill_paths(self, active_skills):
        self.skill_path_requests.append(active_skills)
        return [f"D:/skills/{name}" for name in active_skills]

    def get_skill_instructions(self, active_skills, allow_local_scripts=False):
        self.instruction_requests.append((active_skills, allow_local_scripts))
        return "SKILL-INSTRUCTIONS"

    def get_available_tools(self, context):
        self.tool_contexts.append(context)
        return [{"name": "inspect"}]


class FakeLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


class AgentChatSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepares_default_model_context_prompt_history_and_tools(self):
        memory_store = FakeMemoryStore()
        dispatcher = FakeDispatcher()
        active_sessions = {
            "sid-1": {
                "info": {
                    "asset_type": "virtual",
                    "protocol": "virtual",
                    "host": "workspace",
                    "active_skills": ["skill-creator"],
                    "allow_modifications": True,
                }
            }
        }

        with patch(
            "core.agent_chat_setup.build_vault_rag_context_for_prompt",
            return_value={
                "context": "RAG-CONTEXT",
                "references": [
                    {
                        "source_type": "rag",
                        "title": "巡检资料",
                        "summary_preview": "CPU 正常",
                    }
                ],
            },
        ):
            run = await prepare_chat_agent_run(
                session_id="sid-1",
                user_message="检查技能",
                user_display_message="检查技能-展示",
                model_name=None,
                user_attachments=None,
                active_sessions=active_sessions,
                dispatcher=dispatcher,
                memory_store=memory_store,
                event_logger=FakeLogger(),
                default_model_resolver=lambda: "default-model",
                embedding_resolver=lambda model: (f"emb:{model}", "embedding-model"),
                profile_loader=lambda profile: f"BASE:{profile}",
            )

        self.assertEqual(run.model_name, "default-model")
        self.assertEqual(run.embedding_client, "emb:default-model")
        self.assertEqual(run.embedding_model, "embedding-model")
        self.assertEqual(run.session_context.agent_profile, "default")
        self.assertEqual(run.session_context.host, "workspace")
        self.assertEqual(
            memory_store.ltm_calls,
            [(
                "sid-1",
                "检查技能",
                "emb:default-model",
                "embedding-model",
                [
                    "sid-1",
                    "asset:virtual:workspace:",
                    "asset-host:workspace",
                    "asset-kind:virtual:virtual",
                ],
            )],
        )
        self.assertIn("BASE:default", run.messages[0]["content"])
        self.assertIn("SKILL-INSTRUCTIONS", run.messages[0]["content"])
        self.assertIn("LTM-CONTEXT", run.messages[0]["content"])
        self.assertIn("RAG-CONTEXT", run.messages[0]["content"])
        self.assertEqual(run.messages[1], {"role": "assistant", "content": "历史"})
        self.assertEqual(run.messages[-1], {"role": "user", "content": "检查技能"})
        self.assertEqual(
            memory_store.appended,
            [("sid-1", {"role": "user", "content": "检查技能-展示"})],
        )
        self.assertEqual(dispatcher.skill_path_requests, [["skill-creator"]])
        self.assertEqual(dispatcher.instruction_requests, [(["skill-creator"], True)])
        self.assertEqual(run.tools, [{"name": "inspect"}])
        self.assertEqual(run.memory_references[0]["source_type"], "system_prompt")
        self.assertEqual(run.memory_references[0]["kind_label"], "默认提示词")
        self.assertEqual(run.memory_references[1]["scope_id"], "sid-1")
        self.assertEqual(run.memory_references[2]["source_type"], "rag")
        self.assertEqual(run.context["session_id"], "sid-1")
        self.assertEqual(run.context["active_skill_paths"], ["D:/skills/skill-creator"])
        self.assertEqual(dispatcher.tool_contexts, [run.context])

    async def test_uses_explicit_model_without_default_resolver(self):
        default_calls = []

        run = await prepare_chat_agent_run(
            session_id="sid-1",
            user_message="hi",
            user_display_message=None,
            model_name="chosen-model",
            user_attachments=[],
            active_sessions={"sid-1": {"info": {"host": "10.0.0.1"}}},
            dispatcher=FakeDispatcher(),
            memory_store=FakeMemoryStore(),
            event_logger=FakeLogger(),
            default_model_resolver=lambda: default_calls.append("called") or "default",
            embedding_resolver=lambda model: (f"emb:{model}", "embedding-model"),
            profile_loader=lambda profile: f"BASE:{profile}",
        )

        self.assertEqual(run.model_name, "chosen-model")
        self.assertEqual(default_calls, [])

    async def test_uses_latest_same_asset_profile_when_session_profile_missing(self):
        memory_store = FakeMemoryStore()
        memory_store.asset_profile_for_context = {
            "profile_prompt": "同资产历史画像：这是 Linux 应用服务器，优先关注 SSH、Docker 和安全日志。"
        }

        with patch(
            "core.agent_chat_setup.build_vault_rag_context_for_prompt",
            return_value={"context": "", "references": []},
        ):
            run = await prepare_chat_agent_run(
                session_id="sid-new",
                user_message="继续巡检",
                user_display_message=None,
                model_name="model-a",
                user_attachments=[],
                active_sessions={
                    "sid-new": {
                        "info": {
                            "asset_type": "linux",
                            "protocol": "ssh",
                            "host": "10.0.0.1",
                            "port": 22,
                        }
                    }
                },
                dispatcher=FakeDispatcher(),
                memory_store=memory_store,
                event_logger=FakeLogger(),
                default_model_resolver=lambda: "default-model",
                embedding_resolver=lambda model: (f"emb:{model}", "embedding-model"),
                profile_loader=lambda profile: f"BASE:{profile}",
            )

        self.assertIn("同资产历史画像", run.messages[0]["content"])
        self.assertEqual(
            memory_store.asset_profile_context_calls,
            [("sid-new", "linux:ssh:10.0.0.1:22", "10.0.0.1")],
        )
        self.assertEqual(run.memory_references[0]["source_type"], "system_prompt")
        self.assertEqual(run.memory_references[1]["source_type"], "asset_profile")
        self.assertEqual(run.memory_references[1]["kind_label"], "资产画像")
        self.assertIn("同资产历史画像", run.memory_references[1]["summary_preview"])


if __name__ == "__main__":
    unittest.main()
