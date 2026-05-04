import asyncio
import unittest

from core.agent_ltm import retrieve_ltm_context, retrieve_ltm_context_with_references, schedule_ltm_compression


class FakeLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


class FakeMemoryStore:
    def __init__(self, *, retrieve_error=None):
        self.retrieve_error = retrieve_error
        self.retrieve_calls = []
        self.compress_calls = []

    async def retrieve_ltm(
        self,
        session_id,
        user_message,
        emb_client,
        embedding_model,
        memory_scope_ids=None,
    ):
        self.retrieve_calls.append(
            (session_id, user_message, emb_client, embedding_model, memory_scope_ids)
        )
        if self.retrieve_error:
            raise self.retrieve_error
        return "历史摘要"

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
        return context, [{"scope_id": "sid-ltm", "summary_preview": "历史摘要"}]

    async def compress_and_store_ltm(
        self,
        session_id,
        emb_client,
        embedding_model,
        primary_model_id=None,
        memory_scope_ids=None,
    ):
        self.compress_calls.append(
            (session_id, emb_client, embedding_model, primary_model_id, memory_scope_ids)
        )


class AgentLongTermMemoryTests(unittest.TestCase):
    def test_retrieve_ltm_context_returns_store_context(self):
        memory_store = FakeMemoryStore()
        logger = FakeLogger()

        result = asyncio.run(
            retrieve_ltm_context(
                memory_store=memory_store,
                session_id="sid-ltm",
                user_message="检查数据库",
                emb_client="emb-client",
                embedding_model="emb-model",
                memory_scope_ids=["sid-ltm", "asset:ssh:10.0.0.1:22"],
                event_logger=logger,
            )
        )

        self.assertEqual(result, "历史摘要")
        self.assertEqual(
            memory_store.retrieve_calls,
            [(
                "sid-ltm",
                "检查数据库",
                "emb-client",
                "emb-model",
                ["sid-ltm", "asset:ssh:10.0.0.1:22"],
            )],
        )
        self.assertEqual(logger.errors, [])

    def test_retrieve_ltm_context_falls_back_to_empty_string_on_error(self):
        memory_store = FakeMemoryStore(retrieve_error=RuntimeError("boom"))
        logger = FakeLogger()

        result = asyncio.run(
            retrieve_ltm_context(
                memory_store=memory_store,
                session_id="sid-ltm",
                user_message="检查数据库",
                emb_client="emb-client",
                embedding_model="emb-model",
                event_logger=logger,
            )
        )

        self.assertEqual(result, "")
        self.assertEqual(logger.errors, ["LTM retrieve error: boom"])

    def test_retrieve_ltm_context_with_references_returns_metadata(self):
        memory_store = FakeMemoryStore()
        logger = FakeLogger()

        result = asyncio.run(
            retrieve_ltm_context_with_references(
                memory_store=memory_store,
                session_id="sid-ltm",
                user_message="检查数据库",
                emb_client="emb-client",
                embedding_model="emb-model",
                event_logger=logger,
            )
        )

        self.assertEqual(result.context, "历史摘要")
        self.assertEqual(result.references[0]["scope_id"], "sid-ltm")

    def test_schedule_ltm_compression_creates_background_task(self):
        async def run_case():
            memory_store = FakeMemoryStore()
            task = schedule_ltm_compression(
                memory_store=memory_store,
                session_id="sid-ltm",
                emb_client="emb-client",
                embedding_model="emb-model",
            )
            await task
            return memory_store.compress_calls

        self.assertEqual(
            asyncio.run(run_case()),
            [("sid-ltm", "emb-client", "emb-model", None, None)],
        )


if __name__ == "__main__":
    unittest.main()
