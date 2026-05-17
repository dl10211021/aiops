import unittest
from unittest.mock import patch

from core.agent_session_context import build_agent_session_context
from core.context_engine import build_chat_context_bundle


class FakeMemoryStore:
    def __init__(self):
        self.ltm_calls = []
        self.asset_profile = None

    async def retrieve_ltm_with_references(
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
        return "LTM-CONTEXT", [
            {"source_type": "ltm", "scope_id": session_id, "summary_preview": "历史"}
        ]

    def get_asset_profile(self, session_id):
        self.asset_profile_session_id = session_id
        return self.asset_profile


class FakeLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


class ContextEngineTests(unittest.IsolatedAsyncioTestCase):
    def _session_context(self):
        return build_agent_session_context(
            "sid-ctx",
            {
                "asset_type": "linux",
                "protocol": "ssh",
                "host": "10.0.0.1",
                "port": 22,
                "active_skills": [],
            },
            skill_path_resolver=lambda active_skills: [],
        )

    async def test_build_chat_context_bundle_collects_read_only_sources(self):
        memory_store = FakeMemoryStore()
        memory_store.asset_profile = {
            "session_id": "sid-ctx",
            "role_label": "生产主机",
            "profile_prompt": "资产画像：生产主机，优先关注 CPU 和日志。",
        }

        with patch(
            "core.context_engine.build_vault_rag_context_for_prompt",
            return_value={
                "context": "RAG-CONTEXT",
                "references": [
                    {
                        "source_type": "rag",
                        "title": "Linux 运维手册",
                        "summary_preview": "CPU 检查",
                    }
                ],
            },
        ):
            bundle = await build_chat_context_bundle(
                memory_store=memory_store,
                session_id="sid-ctx",
                session_context=self._session_context(),
                agent_profile="default",
                base_prompt="BASE-PROMPT",
                user_message="检查 CPU",
                emb_client="emb",
                embedding_model="embedding-model",
                event_logger=FakeLogger(),
            )

        self.assertEqual(bundle.ltm_context, "LTM-CONTEXT")
        self.assertEqual(bundle.rag_context, "RAG-CONTEXT")
        self.assertIn("资产画像：生产主机", bundle.asset_profile_prompt)
        self.assertTrue(bundle.has_ltm_context)
        self.assertTrue(bundle.has_rag_context)
        self.assertTrue(bundle.has_asset_profile)
        self.assertEqual(
            memory_store.ltm_calls,
            [("sid-ctx", "检查 CPU", "emb", "embedding-model", ["sid-ctx"])],
        )
        self.assertEqual(memory_store.asset_profile_session_id, "sid-ctx")
        self.assertEqual(
            [ref["source_type"] for ref in bundle.references],
            ["system_prompt", "asset_profile", "ltm", "rag"],
        )

    async def test_build_chat_context_bundle_logs_rag_failure_and_keeps_ltm(self):
        logger = FakeLogger()

        with patch(
            "core.context_engine.build_vault_rag_context_for_prompt",
            side_effect=RuntimeError("rag down"),
        ):
            bundle = await build_chat_context_bundle(
                memory_store=FakeMemoryStore(),
                session_id="sid-ctx",
                session_context=self._session_context(),
                agent_profile="default",
                base_prompt="BASE-PROMPT",
                user_message="检查 CPU",
                emb_client="emb",
                embedding_model="embedding-model",
                event_logger=logger,
            )

        self.assertEqual(bundle.ltm_context, "LTM-CONTEXT")
        self.assertEqual(bundle.rag_context, "")
        self.assertFalse(bundle.has_rag_context)
        self.assertEqual(logger.errors, ["RAG retrieve error: rag down"])


if __name__ == "__main__":
    unittest.main()
