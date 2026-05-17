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
        return context, [{"scope_id": session_id, "summary_preview": "LTM-CONTEXT"}]

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
                ["sid-1"],
            )],
        )
        self.assertIn("BASE:default", run.messages[0]["content"])
        self.assertIn("SKILL-INSTRUCTIONS", run.messages[0]["content"])
        self.assertIn("LTM-CONTEXT", run.messages[0]["content"])
        self.assertIn("RAG-CONTEXT", run.messages[0]["content"])
        self.assertIn("根据知识库资料", run.messages[0]["content"])
        self.assertIn("不要先调用当前会话的数据库/SSH/WinRM/CLI 工具", run.messages[0]["content"])
        self.assertIn("优先调用 `browser_navigate`", run.messages[0]["content"])
        self.assertIn("浏览器工具是联网研究主路径", run.messages[0]["content"])
        self.assertIn("优先使用中文关键词和中国搜索入口", run.messages[0]["content"])
        self.assertIn("至少核对 2 个可信来源", run.messages[0]["content"])
        self.assertIn("先用 `browser_navigate` 打开可信搜索入口扩展候选来源", run.messages[0]["content"])
        self.assertIn("不要停在“我再试试”这类半句话", run.messages[0]["content"])
        self.assertIn("不要把联网查询误当成当前资产巡检", run.messages[0]["content"])
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
        self.assertEqual(run.context["prompt_modules"]["version"], 1)
        self.assertEqual(run.context["prompt_modules"]["surface"], "chat")
        self.assertIn("evidence_contract", run.context["prompt_modules"]["modules"])
        self.assertIn("context_precedence", run.context["prompt_modules"]["modules"])
        self.assertTrue(run.context["prompt_modules"]["enabled"]["skill_instructions"])
        self.assertTrue(run.context["prompt_modules"]["enabled"]["rag_context"])
        self.assertTrue(run.context["prompt_modules"]["enabled"]["ltm_context"])
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

    async def test_does_not_use_same_asset_profile_when_session_profile_missing(self):
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

        self.assertNotIn("同资产历史画像", run.messages[0]["content"])
        self.assertEqual(memory_store.asset_profile_context_calls, [])
        self.assertEqual(run.memory_references[0]["source_type"], "system_prompt")
        self.assertEqual(run.memory_references[1]["scope_id"], "sid-new")
        self.assertFalse(any(ref.get("source_type") == "asset_profile" for ref in run.memory_references))

    async def test_ltm_scope_is_session_only_even_for_database_assets(self):
        memory_store = FakeMemoryStore()

        with patch(
            "core.agent_chat_setup.build_vault_rag_context_for_prompt",
            return_value={"context": "", "references": []},
        ):
            run = await prepare_chat_agent_run(
                session_id="SID-Oracle-A",
                user_message="检查 Oracle 会话",
                user_display_message=None,
                model_name="model-a",
                user_attachments=[],
                active_sessions={
                    "SID-Oracle-A": {
                        "info": {
                            "asset_type": "oracle",
                            "protocol": "oracle",
                            "host": "172.17.8.150",
                            "port": 1521,
                            "username": "system",
                            "extra_args": {"service_name": "ORCL"},
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

        self.assertEqual(
            memory_store.ltm_calls,
            [(
                "SID-Oracle-A",
                "检查 Oracle 会话",
                "emb:model-a",
                "embedding-model",
                ["sid-oracle-a"],
            )],
        )
        self.assertEqual(run.context["memory_scope_ids"], ["sid-oracle-a"])
        self.assertFalse(any(scope.startswith("asset") for scope in run.context["memory_scope_ids"]))
        self.assertEqual(run.memory_references[1]["scope_id"], "SID-Oracle-A")

    async def test_analysis_only_run_disables_tools(self):
        dispatcher = FakeDispatcher()

        with patch(
            "core.agent_chat_setup.build_vault_rag_context_for_prompt",
            return_value={"context": "", "references": []},
        ):
            run = await prepare_chat_agent_run(
                session_id="sid-term",
                user_message="【SSH终端记录】\n```text\n$ ls\nfile\n```",
                user_display_message=None,
                model_name="model-a",
                user_attachments=[],
                active_sessions={
                    "sid-term": {
                        "info": {
                            "asset_type": "linux",
                            "protocol": "ssh",
                            "host": "172.17.10.2",
                            "port": 22,
                        }
                    }
                },
                dispatcher=dispatcher,
                memory_store=FakeMemoryStore(),
                event_logger=FakeLogger(),
                default_model_resolver=lambda: "default-model",
                embedding_resolver=lambda model: (f"emb:{model}", "embedding-model"),
                analysis_only=True,
                profile_loader=lambda profile: f"BASE:{profile}",
            )

        self.assertEqual(run.tools, [])
        self.assertEqual(dispatcher.tool_contexts, [])
        self.assertTrue(run.context["analysis_only"])
        self.assertTrue(run.context["prompt_modules"]["enabled"]["analysis_only"])
        self.assertIn("analysis_only", run.context["prompt_modules"]["modules"])
        self.assertIn("本轮终端记录分析模式", run.messages[0]["content"])
        self.assertIn("不得调用任何工具", run.messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
