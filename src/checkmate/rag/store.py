"""Qdrant-backed vector store. One collection per repo."""
from __future__ import annotations

import logging
import re
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from checkmate.config import settings
from checkmate.rag.chunker import Chunk
from checkmate.rag.embedder import EMBED_DIM

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def collection_name(repo_full_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", repo_full_name).strip("_").lower()
    return f"repo_{slug}"


def ensure_collection(repo_full_name: str) -> str:
    """Create the Qdrant collection for a repo if it doesn't exist.

    Returns the collection name.
    """
    name = collection_name(repo_full_name)
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if name not in existing:
        logger.info("creating qdrant collection %s", name)
        c.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
        )
    return name


def collection_count(repo_full_name: str) -> int:
    name = collection_name(repo_full_name)
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if name not in existing:
        return 0
    return c.count(collection_name=name, exact=True).count


def upsert_chunks(repo_full_name: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    if not chunks:
        return
    name = ensure_collection(repo_full_name)
    points = [
        qm.PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "path": ch.path,
                "start_line": ch.start_line,
                "end_line": ch.end_line,
                "symbol": ch.symbol,
                "content": ch.content,
            },
        )
        for ch, vec in zip(chunks, vectors, strict=True)
    ]
    client().upsert(collection_name=name, points=points, wait=True)


def search(
    repo_full_name: str,
    query_vector: list[float],
    top_k: int = 8,
    exclude_paths: set[str] | None = None,
) -> list[dict]:
    name = collection_name(repo_full_name)
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if name not in existing:
        return []

    query_filter = None
    if exclude_paths:
        query_filter = qm.Filter(
            must_not=[
                qm.FieldCondition(key="path", match=qm.MatchValue(value=p))
                for p in exclude_paths
            ]
        )

    result = c.query_points(
        collection_name=name,
        query=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )
    return [
        {**h.payload, "score": h.score}
        for h in result.points
    ]


def delete_collection(repo_full_name: str) -> None:
    name = collection_name(repo_full_name)
    try:
        client().delete_collection(collection_name=name)
    except Exception as e:
        logger.warning("delete_collection(%s) failed: %s", name, e)
