"""Promptfoo custom provider — dispatches to the Checkmate review engine.

Promptfoo calls `call_api(prompt, options, context)` for each test case.
We ignore `prompt` (our review engine is driven by the test-case vars) and
use `context["vars"]` to reconstruct the review call.

Usage from promptfoo.config.yaml:
    providers:
      - file://evals/provider.py:call_api
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure src/ is on the path when promptfoo runs this file directly.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Disable Langfuse during evals — don't pollute the prod trace stream.
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

from checkmate.review import review_diff  # noqa: E402


def call_api(prompt, options, context):
    vars_ = (context or {}).get("vars", {}) or {}
    diff = vars_.get("diff", "")
    try:
        review = review_diff(
            repo=vars_.get("repo", "demo/repo"),
            pr_number=int(vars_.get("pr_number", 1)),
            pr_title=vars_.get("pr_title", "Eval test PR"),
            pr_body=vars_.get("pr_body", ""),
            diff=diff,
            repo_context=vars_.get("repo_context", ""),
        )
        output = review.model_dump()
        return {
            "output": json.dumps(output),
            "metadata": {
                "findings_count": len(output["findings"]),
                "categories": sorted({f["category"] for f in output["findings"]}),
                "severities": sorted({f["severity"] for f in output["findings"]}),
            },
        }
    except Exception as e:
        return {"output": "", "error": f"{type(e).__name__}: {e}"}
