import asyncio
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from core.local_embedding import (
    DEFAULT_LOCAL_EMBEDDING_MODEL,
    LocalEmbeddingClient,
    is_local_embedding_model_id,
    normalize_local_embedding_model_id,
)


class _FakeSentenceTransformer:
    def __init__(self, model_path, device="cpu"):
        self.model_path = model_path
        self.device = device

    def encode(self, texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False):
        return [[0.1, 0.2, 0.3] for _ in texts]


class TestLocalEmbedding(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path.cwd() / "tests" / "tmp_local_embedding"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.tmpdir.exists():
            self.tmpdir.rmdir()

    def test_local_embedding_model_id_detection(self):
        self.assertTrue(is_local_embedding_model_id(DEFAULT_LOCAL_EMBEDDING_MODEL))
        self.assertTrue(is_local_embedding_model_id("Qwen/Qwen3-Embedding-0.6B"))
        self.assertEqual(
            normalize_local_embedding_model_id("Qwen/Qwen3-Embedding-0.6B"),
            DEFAULT_LOCAL_EMBEDDING_MODEL,
        )

    def test_local_embedding_client_matches_openai_embedding_shape(self):
        fake_module = types.SimpleNamespace(SentenceTransformer=_FakeSentenceTransformer)
        with patch.dict("sys.modules", {"sentence_transformers": fake_module}):
            client = LocalEmbeddingClient(self.tmpdir)
            response = asyncio.run(client.embeddings.create(input=["测试", "知识库"], model=DEFAULT_LOCAL_EMBEDDING_MODEL))

        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0].embedding, [0.1, 0.2, 0.3])


if __name__ == "__main__":
    unittest.main()
