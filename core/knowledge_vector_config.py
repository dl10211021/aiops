from __future__ import annotations


DEFAULT_KNOWLEDGE_VECTOR_TABLE = "knowledge_base"
LEGACY_KNOWLEDGE_VECTOR_DIM = 3072


def knowledge_vector_table_name(embedding_dim: int | str | None) -> str:
    try:
        dim = int(embedding_dim or LEGACY_KNOWLEDGE_VECTOR_DIM)
    except (TypeError, ValueError):
        dim = LEGACY_KNOWLEDGE_VECTOR_DIM
    if dim == LEGACY_KNOWLEDGE_VECTOR_DIM:
        return DEFAULT_KNOWLEDGE_VECTOR_TABLE
    return f"{DEFAULT_KNOWLEDGE_VECTOR_TABLE}_{dim}"
