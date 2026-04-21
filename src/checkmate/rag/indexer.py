"""Walk a repo, chunk sources, embed, upsert to Qdrant.

Two entry points:
  - index_local_path(repo, path): index a directory on disk (smoke-testing)
  - ensure_indexed(repo, installation_id): fetch a tarball from GitHub and
    index it if the repo isn't already in Qdrant. Cheap no-op if it is.
"""
from __future__ import annotations

import io
import logging
import os
import tarfile
import tempfile
from pathlib import Path

import httpx

from checkmate.rag.chunker import SOURCE_EXTENSIONS, Chunk, chunk_file
from checkmate.rag.embedder import embed_batch
from checkmate.rag.store import collection_count, upsert_chunks

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 100_000
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "target", "vendor", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "coverage", ".idea", ".vscode",
}
EMBED_BATCH = 64


def _iter_source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SOURCE_EXTENSIONS:
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def index_local_path(repo_full_name: str, root: str | Path) -> int:
    """Index a local directory. Returns the number of chunks indexed."""
    root = Path(root)
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")

    all_chunks: list[Chunk] = []
    for p in _iter_source_files(root):
        text = _read_text(p)
        if text is None:
            continue
        rel = p.relative_to(root).as_posix()
        all_chunks.extend(chunk_file(rel, text))

    if not all_chunks:
        logger.info("no source files found under %s", root)
        return 0

    logger.info("embedding %d chunks from %s", len(all_chunks), repo_full_name)
    for i in range(0, len(all_chunks), EMBED_BATCH):
        batch = all_chunks[i : i + EMBED_BATCH]
        vecs = embed_batch([c.content for c in batch])
        upsert_chunks(repo_full_name, batch, vecs)

    logger.info("indexed %d chunks for %s", len(all_chunks), repo_full_name)
    return len(all_chunks)


async def _fetch_tarball(repo_full_name: str, ref: str, token: str) -> bytes:
    """Download a repo tarball via the GitHub API."""
    url = f"https://api.github.com/repos/{repo_full_name}/tarball/{ref}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as c:
        resp = await c.get(url, headers=headers)
    resp.raise_for_status()
    return resp.content


def _extract_tarball(data: bytes, dest: Path) -> Path:
    """Extract tarball into dest/ and return the single top-level repo dir."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        tf.extractall(dest)  # noqa: S202 - trusted source (GitHub API)
    entries = [p for p in dest.iterdir() if p.is_dir()]
    if not entries:
        raise RuntimeError("tarball had no top-level directory")
    return entries[0]


async def ensure_indexed(
    repo_full_name: str,
    ref: str,
    installation_token_value: str,
    force: bool = False,
) -> int:
    """Index the repo at `ref` if it isn't already. Returns chunk count indexed (0 if cached)."""
    if not force and collection_count(repo_full_name) > 0:
        logger.info("repo %s already indexed — skipping", repo_full_name)
        return 0

    logger.info("fetching tarball for %s@%s", repo_full_name, ref)
    data = await _fetch_tarball(repo_full_name, ref, installation_token_value)

    with tempfile.TemporaryDirectory() as tmp:
        root = _extract_tarball(data, Path(tmp))
        return index_local_path(repo_full_name, root)
