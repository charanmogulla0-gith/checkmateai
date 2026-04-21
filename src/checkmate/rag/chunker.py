"""Split source files into retrieval-sized chunks.

Python files use `ast` so each chunk is a top-level function/class — these
align with how reviewers actually think about context. Everything else falls
back to a fixed line window with overlap.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

MAX_CHUNK_CHARS = 4_000
WINDOW_LINES = 60
WINDOW_OVERLAP = 15

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".scala", ".sh", ".bash", ".sql", ".yaml", ".yml", ".toml",
}


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int
    end_line: int
    symbol: str
    content: str


def chunk_file(path: str, content: str) -> list[Chunk]:
    """Return chunks for a single source file.

    path is the relative path used as-is in chunk metadata.
    """
    if path.endswith(".py"):
        try:
            return _chunk_python(path, content)
        except SyntaxError:
            pass  # malformed Python — fall through to line windows
    return _chunk_lines(path, content)


def _chunk_python(path: str, content: str) -> list[Chunk]:
    tree = ast.parse(content)
    lines = content.splitlines()
    out: list[Chunk] = []

    top_nodes = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]

    if not top_nodes:
        return _chunk_lines(path, content)

    # Module-level preamble (imports/constants before the first def)
    first_start = min(n.lineno for n in top_nodes)
    if first_start > 1:
        preamble = "\n".join(lines[: first_start - 1]).strip()
        if preamble:
            out.append(Chunk(
                path=path, start_line=1, end_line=first_start - 1,
                symbol="<module>", content=preamble[:MAX_CHUNK_CHARS],
            ))

    for node in top_nodes:
        start = node.lineno
        end = node.end_lineno or start
        body = "\n".join(lines[start - 1 : end])
        if not body.strip():
            continue
        kind = "class" if isinstance(node, ast.ClassDef) else "def"
        out.append(Chunk(
            path=path, start_line=start, end_line=end,
            symbol=f"{kind} {node.name}", content=body[:MAX_CHUNK_CHARS],
        ))

    return out


def _chunk_lines(path: str, content: str) -> list[Chunk]:
    lines = content.splitlines()
    if not lines:
        return []
    out: list[Chunk] = []
    i = 0
    while i < len(lines):
        end = min(i + WINDOW_LINES, len(lines))
        body = "\n".join(lines[i:end])
        if body.strip():
            out.append(Chunk(
                path=path, start_line=i + 1, end_line=end,
                symbol="", content=body[:MAX_CHUNK_CHARS],
            ))
        if end == len(lines):
            break
        i = end - WINDOW_OVERLAP
    return out
