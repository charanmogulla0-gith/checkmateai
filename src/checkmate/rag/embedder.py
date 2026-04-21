"""Local embedding model (BGE-small, 384d, ~33M params, CPU-friendly).

The model is lazy-loaded on first call so importing this module stays fast.
First call downloads weights to ~/.cache/huggingface (~130MB) — one-time cost.
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    logger.info("loading embedding model %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vecs = _model().encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vecs.tolist()


def embed_one(text: str) -> list[float]:
    return embed_batch([text])[0]
