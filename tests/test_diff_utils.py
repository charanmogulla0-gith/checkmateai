from checkmate.diff_utils import commentable_lines, truncate_diff


SAMPLE_DIFF = """diff --git a/foo.py b/foo.py
index 111..222 100644
--- a/foo.py
+++ b/foo.py
@@ -1,5 +1,6 @@
 def add(a, b):
-    return a - b
+    return a + b
+    # fixed

 def sub(a, b):
     return a - b
"""


def test_commentable_lines_includes_added_and_context() -> None:
    lines = commentable_lines(SAMPLE_DIFF)
    assert "foo.py" in lines
    # `return a + b` is line 2 in the new file; the new comment is line 3
    assert 2 in lines["foo.py"]
    assert 3 in lines["foo.py"]


def test_truncate_diff_noop_under_limit() -> None:
    assert truncate_diff("hello", max_chars=100) == "hello"


def test_truncate_diff_truncates_over_limit() -> None:
    big = "x" * 200
    out = truncate_diff(big, max_chars=100)
    assert len(out) <= 200
    assert "truncated" in out
