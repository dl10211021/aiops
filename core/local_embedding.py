from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_EMBEDDING_MODEL = "local:qwen3-embedding-0.6b"
DEFAULT_LOCAL_EMBEDDING_REPO_ID = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_LOCAL_EMBEDDING_DIM = 1024
DEFAULT_LOCAL_EMBEDDING_PATH = PROJECT_ROOT / "models" / "embeddings" / "qwen3-embedding-0.6b"


def _as_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def is_local_embedding_model_id(model_id: str | None) -> bool:
    value = str(model_id or "").strip()
    if not value:
        return False
    if value in {DEFAULT_LOCAL_EMBEDDING_MODEL, DEFAULT_LOCAL_EMBEDDING_REPO_ID, "qwen3-embedding-0.6b"}:
        return True
    if value.startswith("local:"):
        return True
    try:
        return _as_path(value).exists()
    except OSError:
        return False


def local_embedding_model_available() -> bool:
    return resolve_local_embedding_path().exists()


def normalize_local_embedding_model_id(model_id: str | None = None) -> str:
    value = str(model_id or "").strip()
    if not value or value in {DEFAULT_LOCAL_EMBEDDING_REPO_ID, "qwen3-embedding-0.6b"}:
        return DEFAULT_LOCAL_EMBEDDING_MODEL
    if value.startswith("local:"):
        return value
    if _as_path(value).exists():
        return value
    return DEFAULT_LOCAL_EMBEDDING_MODEL


def resolve_local_embedding_path(model_id: str | None = None) -> Path:
    configured = os.environ.get("OPSCORE_LOCAL_EMBEDDING_PATH") or os.environ.get("LOCAL_EMBEDDING_PATH")
    if configured:
        return _as_path(configured)

    value = str(model_id or "").strip()
    if value and not value.startswith("local:") and value not in {DEFAULT_LOCAL_EMBEDDING_REPO_ID, "qwen3-embedding-0.6b"}:
        candidate = _as_path(value)
        if candidate.exists():
            return candidate

    if value.startswith("local:") and value != DEFAULT_LOCAL_EMBEDDING_MODEL:
        slug = value.split(":", 1)[1].strip().strip("/\\")
        if slug:
            return PROJECT_ROOT / "models" / "embeddings" / slug

    return DEFAULT_LOCAL_EMBEDDING_PATH


@dataclass
class LocalEmbeddingData:
    embedding: list[float]


@dataclass
class LocalEmbeddingResponse:
    data: list[LocalEmbeddingData]


class LocalEmbeddingResource:
    def __init__(self, owner: "LocalEmbeddingClient") -> None:
        self._owner = owner

    async def create(self, *, input, model: str | None = None):
        vectors = await asyncio.to_thread(self._owner.encode, input)
        return LocalEmbeddingResponse(data=[LocalEmbeddingData(embedding=vector) for vector in vectors])


class LocalEmbeddingClient:
    """OpenAI-compatible local embedding client backed by SentenceTransformer."""

    def __init__(self, model_path: str | os.PathLike[str] | None = None, *, device: str | None = None) -> None:
        self.model_path = _as_path(model_path or resolve_local_embedding_path())
        self.device = device or os.environ.get("OPSCORE_EMBEDDING_DEVICE") or "cpu"
        self.embeddings = LocalEmbeddingResource(self)
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        if not self.model_path.exists():
            raise FileNotFoundError(
                "本地向量模型不存在："
                f"{self.model_path}。请先运行 scripts/download_embedding_model.py 下载模型。"
            )
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            raise RuntimeError(
                "缺少本地向量运行依赖 sentence-transformers，请安装 requirements.txt 后重试。"
            ) from exc
        self._model = SentenceTransformer(str(self.model_path), device=self.device)
        return self._model

    def encode(self, input_value) -> list[list[float]]:
        model = self._load_model()
        texts = _normalize_embedding_input(input_value)
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if hasattr(vectors, "tolist"):
            vectors = vectors.tolist()
        if vectors and isinstance(vectors[0], (int, float)):
            vectors = [vectors]
        return [[float(value) for value in row] for row in vectors]


def _normalize_embedding_input(input_value) -> list[str]:
    if isinstance(input_value, str):
        return [input_value]
    if isinstance(input_value, Iterable):
        return [str(item) for item in input_value]
    return [str(input_value)]


def get_local_embedding_client(model_id: str | None = None) -> LocalEmbeddingClient:
    return LocalEmbeddingClient(resolve_local_embedding_path(model_id))
