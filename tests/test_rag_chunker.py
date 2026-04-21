"""Chunker is pure-Python and has no external dependencies — easy to unit test."""
from checkmate.rag.chunker import chunk_file


def test_python_file_splits_by_function_and_class():
    src = (
        "import os\n"
        "\n"
        "CONST = 42\n"
        "\n"
        "def foo(x):\n"
        "    return x + 1\n"
        "\n"
        "class Bar:\n"
        "    def method(self):\n"
        "        return 'hi'\n"
    )
    chunks = chunk_file("example.py", src)
    symbols = [c.symbol for c in chunks]
    assert "<module>" in symbols
    assert "def foo" in symbols
    assert "class Bar" in symbols


def test_python_syntax_error_falls_back_to_line_windows():
    src = "def broken(\n  missing paren\n" + "x = 1\n" * 80
    chunks = chunk_file("bad.py", src)
    assert len(chunks) >= 1
    assert all(c.symbol == "" for c in chunks)


def test_non_python_uses_line_windows():
    src = "\n".join(f"line {i}" for i in range(150))
    chunks = chunk_file("notes.txt", src)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.end_line - c.start_line + 1 <= 60


def test_empty_file_returns_no_chunks():
    assert chunk_file("empty.py", "") == []
