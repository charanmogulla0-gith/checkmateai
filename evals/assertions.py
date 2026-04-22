"""Assertion helpers for promptfoo — invoked via file:// python assertions.

Each function takes (output, context) and returns either True/False or a
dict with {"pass": bool, "score": float, "reason": str}.

`output` is the stringified JSON returned by provider.call_api.
"""
from __future__ import annotations

import json
from typing import Any


def _parse(output: str) -> dict:
    try:
        return json.loads(output)
    except Exception:
        return {"summary": "", "findings": []}


def finds_category(output: str, context: dict[str, Any]) -> dict:
    """Pass if at least one finding matches any expected category.

    Accepts either `expected_category` (string) or `expected_categories`
    (list of strings) — category boundaries overlap in practice (a race is
    both a bug and a concurrency issue) so a single "correct" label is
    often wrong. Prefer `expected_categories` for fair grading.
    """
    vars_ = context.get("vars", {})
    expected = vars_.get("expected_categories") or vars_.get("expected_category")
    if not expected:
        return {"pass": False, "score": 0.0, "reason": "no expected category in vars"}
    if isinstance(expected, str):
        expected = [expected]
    expected_set = set(expected)
    got = [f.get("category") for f in _parse(output).get("findings", [])]
    hit = any(c in expected_set for c in got)
    return {
        "pass": hit,
        "score": 1.0 if hit else 0.0,
        "reason": f"expected any of {sorted(expected_set)!r}; got {got}",
    }


def finds_on_line(output: str, context: dict[str, Any]) -> dict:
    """Pass if at least one finding lands on the expected line.

    Uses `context.vars.expected_line` (int).
    """
    review = _parse(output)
    expected = context.get("vars", {}).get("expected_line")
    if expected is None:
        return {"pass": False, "score": 0.0, "reason": "no expected_line in vars"}
    expected = int(expected)
    hit = any(int(f.get("line", 0)) == expected for f in review.get("findings", []))
    return {
        "pass": hit,
        "score": 1.0 if hit else 0.0,
        "reason": f"expected line {expected}; got {[f.get('line') for f in review.get('findings', [])]}",
    }


def no_false_positives(output: str, context: dict[str, Any]) -> dict:
    """Pass when findings list is empty (for known-clean diffs)."""
    review = _parse(output)
    n = len(review.get("findings", []))
    return {
        "pass": n == 0,
        "score": 1.0 if n == 0 else max(0.0, 1.0 - n * 0.25),
        "reason": f"expected 0 findings; got {n}",
    }


def finds_severity_at_least(output: str, context: dict[str, Any]) -> dict:
    """Pass if at least one finding has severity >= expected (high > medium > low)."""
    review = _parse(output)
    expected = context.get("vars", {}).get("expected_severity", "high")
    order = {"low": 1, "medium": 2, "high": 3}
    target = order.get(expected, 3)
    hit = any(order.get(f.get("severity"), 0) >= target for f in review.get("findings", []))
    return {
        "pass": hit,
        "score": 1.0 if hit else 0.0,
        "reason": f"expected ≥{expected}; got {[f.get('severity') for f in review.get('findings', [])]}",
    }
