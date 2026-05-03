from __future__ import annotations

import logging
import os
import sys


EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "3072"))

logger = logging.getLogger(__name__)


def _sync_agent_compat_globals() -> None:
    agent_module = sys.modules.get("core.agent")
    if agent_module is None:
        return
    setattr(agent_module, "EMBEDDING_MODEL", EMBEDDING_MODEL)
    setattr(agent_module, "EMBEDDING_DIM", EMBEDDING_DIM)


def update_embedding_config(model: str, dim: int) -> None:
    global EMBEDDING_MODEL, EMBEDDING_DIM
    EMBEDDING_MODEL = model
    EMBEDDING_DIM = dim
    _sync_agent_compat_globals()
    logger.info("Embedding config updated: model=%s, dim=%s", model, dim)


def get_embedding_config() -> tuple[str, int]:
    return EMBEDDING_MODEL, EMBEDDING_DIM
