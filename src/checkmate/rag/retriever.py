"""Retrieve repo context relevant to a PR diff."""
from __future__ import annotations

import logging
import re

from unidiff import PatchSet

from checkmate.rag.embedder import embed_one
from checkmate.rag.store import search

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8_000
DEFAULT_TOP_K = 6


def _query_from_diff(diff: str) -> tuple[str, set[str]]:
    """Build a query string from the diff + return the set of changed file paths.

    The query is the union of added lines (the most signal-rich part). Changed
    files are returned so we can exclude them from retrieval (we don't want the
    model to get its own edited file back as "context").
    """
    try:
        patch = PatchSet(diff)
    except Exception:
        return diff[:2_000], set()

    changed_paths: set[str] = set()
    added_lines: list[str] = []
    for pf in patch:
        # unidiff uses 'target_file' like 'b/path/to/file'
        tgt = pf.target_file
        if tgt.startswith("b/"):
            tgt = tgt[2:]
        changed_paths.add(tgt)
        for hunk in pf:
            for line in hunk:
                if line.is_added:
                    added_lines.append(line.value.rstrip())

    query = "\n".join(added_lines)[:4_000]
    # Light-touch signal: also include any identifier tokens from added lines
    # so purely-deletion hunks or tiny edits still produce a usable query.
    if len(query) < 100:
        query = query + "\n" + " ".join(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", diff))[:2_000]
    return query, changed_paths


def _format_context(hits: list[dict]) -> str:
    out_parts: list[str] = []
    budget = MAX_CONTEXT_CHARS
    for h in hits:
        header = f"### {h['path']} (L{h['start_line']}-{h['end_line']})"
        if h.get("symbol"):
            header += f" — `{h['symbol']}`"
        block = f"{header}\n```\n{h['content']}\n```\n"
        if len(block) > budget:
            break
        out_parts.append(block)
        budget -= len(block)
    return "\n".join(out_parts)


def retrieve_context(repo_full_name: str, diff: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Return a formatted context block for the PR, or '' if nothing relevant."""
    query, changed = _query_from_diff(diff)
    if not query.strip():
        return ""
    vec = embed_one(query)
    hits = search(repo_full_name, vec, top_k=top_k, exclude_paths=changed)
    if not hits:
        return ""
    logger.info("retrieved %d chunks for %s (top score=%.3f)",
                len(hits), repo_full_name, hits[0]["score"])
    return _format_context(hits)
