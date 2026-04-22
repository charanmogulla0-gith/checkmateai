"""Native Python runner for the Checkmate eval suite.

Reads `evals/promptfoo.config.yaml`, calls `review_diff` for each test case,
runs each assertion, and prints a summary. Use this as a Windows-friendly
alternative to `promptfoo eval` — same YAML, same assertion helpers.

    .venv/Scripts/python.exe evals/run_evals.py [--filter SUBSTRING]

Exit code is 0 only if every case passes (for CI).
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Silence Langfuse during evals.
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

from checkmate.review import review_diff  # noqa: E402


def _load_python_assertion(ref: str):
    """Resolve `file://evals/assertions.py:finds_category` to the callable."""
    assert ref.startswith("file://"), ref
    path, fn = ref[len("file://") :].split(":")
    spec = importlib.util.spec_from_file_location("_eval_assertions", ROOT / path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn)


def _run_js_assertion(js_src: str, output: str) -> bool:
    """Translate the small JS assertions we use (contains-like) into Python.

    These are intentionally tiny (JSON.parse + shape checks) so a Python port
    is straightforward. Anything more complex should become a Python assertion.
    """
    try:
        r = json.loads(output)
    except Exception:
        return False
    if "typeof r.summary === 'string' && Array.isArray(r.findings)" in js_src:
        return isinstance(r.get("summary"), str) and isinstance(r.get("findings"), list)
    if "r.findings.length >= 1" in js_src and "r.findings.some" in js_src:
        cats = re.findall(r"f\.category === '([^']+)'", js_src)
        return len(r.get("findings", [])) >= 1 and any(
            f.get("category") in cats for f in r["findings"]
        )
    if "r.findings.some(f =>" in js_src and "category ===" in js_src:
        cats = re.findall(r"f\.category === '([^']+)'", js_src)
        return any(f.get("category") in cats for f in r.get("findings", []))
    raise NotImplementedError(f"Unrecognized JS assertion: {js_src[:80]}")


def _evaluate_test(case: dict[str, Any]) -> dict[str, Any]:
    vars_ = case.get("vars", {})
    t0 = time.time()
    try:
        review = review_diff(
            repo=vars_.get("repo", "eval/demo"),
            pr_number=int(vars_.get("pr_number", 1)),
            pr_title=vars_.get("pr_title", "Eval PR"),
            pr_body=vars_.get("pr_body", ""),
            diff=vars_.get("diff", ""),
            repo_context=vars_.get("repo_context", ""),
        )
        output = json.dumps(review.model_dump())
    except Exception as e:
        return {
            "description": case.get("description"),
            "passed": False,
            "score": 0.0,
            "latency_s": time.time() - t0,
            "error": f"{type(e).__name__}: {e}",
            "assertions": [],
        }

    assertions = []
    passed_all = True
    total_score = 0.0
    for a in case.get("assert", []):
        a_type = a.get("type")
        if a_type == "is-json":
            ok = True
            try:
                json.loads(output)
            except Exception:
                ok = False
            assertions.append({"type": a_type, "pass": ok, "reason": ""})
        elif a_type == "javascript":
            ok = _run_js_assertion(a.get("value", ""), output)
            assertions.append({"type": a_type, "pass": ok, "reason": ""})
        elif a_type == "python":
            fn = _load_python_assertion(a.get("value", ""))
            ctx = {"vars": vars_}
            result = fn(output, ctx)
            if isinstance(result, bool):
                ok = result
                reason = ""
                score = 1.0 if ok else 0.0
            else:
                ok = bool(result.get("pass"))
                reason = result.get("reason", "")
                score = float(result.get("score", 1.0 if ok else 0.0))
            assertions.append({"type": a_type, "pass": ok, "reason": reason, "score": score})
        else:
            assertions.append({"type": a_type, "pass": False, "reason": "unsupported"})
            ok = False

        passed_all = passed_all and assertions[-1]["pass"]
        total_score += assertions[-1].get("score", 1.0 if assertions[-1]["pass"] else 0.0)

    return {
        "description": case.get("description"),
        "passed": passed_all,
        "score": total_score / max(1, len(assertions)),
        "latency_s": round(time.time() - t0, 2),
        "output": json.loads(output),
        "assertions": assertions,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--filter", help="substring filter on test description")
    p.add_argument("--config", default="evals/promptfoo.config.yaml")
    p.add_argument("--report", default="evals/results/latest.json")
    args = p.parse_args()

    cfg = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    cases = cfg.get("tests", [])
    if args.filter:
        cases = [c for c in cases if args.filter.lower() in (c.get("description") or "").lower()]
    if not cases:
        print("No cases matched.")
        return 1

    print(f"Running {len(cases)} eval case(s)\n")
    results = []
    pass_count = 0
    for i, case in enumerate(cases, 1):
        desc = case.get("description", "(no description)")
        print(f"[{i:>2}/{len(cases)}] {desc} ... ", end="", flush=True)
        r = _evaluate_test(case)
        results.append(r)
        if r["passed"]:
            pass_count += 1
            print(f"PASS  (score={r['score']:.2f}, {r['latency_s']}s)")
        else:
            print(f"FAIL  ({r['latency_s']}s)")
            if r.get("error"):
                print(f"      error: {r['error']}")
            for a in r["assertions"]:
                if not a["pass"]:
                    print(f"      ✗ {a['type']}: {a.get('reason', '')[:140]}")

    print(f"\n{'='*60}")
    print(f"Results: {pass_count}/{len(cases)} passed "
          f"({pass_count*100//len(cases)}%)")

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {"total": len(cases), "passed": pass_count, "results": results},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"Report written to {report_path}")

    return 0 if pass_count == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
