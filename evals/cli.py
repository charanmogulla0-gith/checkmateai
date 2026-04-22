"""Standalone CLI wrapper — promptfoo's exec: provider calls this.

Input: the rendered prompt arrives on stdin as text. Promptfoo also sets
PROMPTFOO_VARS (JSON-encoded test vars) in the environment so we can
rebuild a structured review_diff call.

Output: JSON object on stdout matching `checkmate.schemas.Review`.
Usage (from promptfoo.config.yaml):
    providers:
      - id: exec:.venv/Scripts/python.exe evals/cli.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Silence Langfuse during evals so we don't pollute the prod trace stream.
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

from checkmate.review import review_diff  # noqa: E402


def main() -> None:
    vars_raw = os.environ.get("PROMPTFOO_VARS", "{}")
    try:
        vars_ = json.loads(vars_raw)
    except json.JSONDecodeError:
        vars_ = {}

    diff = vars_.get("diff") or sys.stdin.read()
    review = review_diff(
        repo=vars_.get("repo", "demo/repo"),
        pr_number=int(vars_.get("pr_number", 1)),
        pr_title=vars_.get("pr_title", "Eval test PR"),
        pr_body=vars_.get("pr_body", ""),
        diff=diff,
        repo_context=vars_.get("repo_context", ""),
    )
    sys.stdout.write(json.dumps(review.model_dump()))


if __name__ == "__main__":
    main()
