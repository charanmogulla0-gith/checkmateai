"""Smoke test: call the review engine on a small synthetic diff.

Run: .venv/Scripts/python.exe scripts/smoke_test_review.py
"""
from checkmate.review import review_diff

DIFF = """diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -10,5 +10,9 @@
 def get_user(user_id):
-    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
+    return db.query(f"SELECT * FROM users WHERE id = {user_id}")
+
+def delete_user(user_id):
+    # NEW: no auth check!
+    db.execute(f"DELETE FROM users WHERE id = {user_id}")
"""


def main() -> None:
    review = review_diff(
        repo="demo/app",
        pr_number=1,
        pr_title="Add delete_user endpoint",
        pr_body="Adds a new endpoint to delete users by ID.",
        diff=DIFF,
    )
    print("=" * 60)
    print("SUMMARY:", review.summary)
    print("=" * 60)
    for f in review.findings:
        print(f"\n[{f.severity}] {f.category} — {f.file}:{f.line}")
        print(f"  {f.comment}")
    print(f"\nTotal findings: {len(review.findings)}")


if __name__ == "__main__":
    main()
