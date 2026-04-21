"""Smoke test for the RAG module.

Indexes the checkmateai repo itself, then retrieves context for a sample diff
that edits the review engine. Run:

    .venv/Scripts/python.exe scripts/smoke_test_rag.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from checkmate.rag.indexer import index_local_path
from checkmate.rag.retriever import retrieve_context
from checkmate.rag.store import collection_count, delete_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("smoke")

REPO = "charanmogulla0-gith/checkmateai"
REPO_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_DIFF = """diff --git a/src/checkmate/review.py b/src/checkmate/review.py
index 111..222 100644
--- a/src/checkmate/review.py
+++ b/src/checkmate/review.py
@@ -50,7 +50,7 @@ def review_diff(
     response = _client.messages.create(
         model=settings.claude_model,
-        max_tokens=MAX_OUTPUT_TOKENS,
+        max_tokens=8192,
         system=[
             {
                 "type": "text",
"""


def main() -> None:
    if "--reset" in sys.argv:
        log.info("dropping existing collection")
        delete_collection(REPO)

    log.info("collection count before index: %d", collection_count(REPO))
    if collection_count(REPO) == 0:
        n = index_local_path(REPO, REPO_ROOT)
        log.info("indexed %d chunks", n)
    else:
        log.info("already indexed — skipping")

    log.info("collection count after index: %d", collection_count(REPO))

    log.info("retrieving context for sample diff...")
    ctx = retrieve_context(REPO, SAMPLE_DIFF, top_k=5)
    print("=" * 72)
    print(ctx if ctx else "(no context returned)")
    print("=" * 72)
    print(f"\ncontext length: {len(ctx)} chars")


if __name__ == "__main__":
    main()
