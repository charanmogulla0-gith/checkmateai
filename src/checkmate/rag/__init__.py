"""Local codebase RAG: chunk → embed (BGE-small) → Qdrant → retrieve."""
from checkmate.rag.indexer import ensure_indexed, index_local_path
from checkmate.rag.retriever import retrieve_context

__all__ = ["ensure_indexed", "index_local_path", "retrieve_context"]
