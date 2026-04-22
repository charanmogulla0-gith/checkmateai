#!/usr/bin/env bash
# Run the Checkmate review-engine eval suite with promptfoo.
#
# Costs ~$0.01 per test case in Anthropic API fees at Sonnet 4.x pricing.
# Output is written to evals/results/ and summarized to stdout.
set -euo pipefail

cd "$(dirname "$0")/.."

export PROMPTFOO_PYTHON="${PROMPTFOO_PYTHON:-.venv/Scripts/python.exe}"
mkdir -p evals/results

promptfoo eval \
  -c evals/promptfoo.config.yaml \
  -o "evals/results/latest.json" \
  --no-cache \
  "$@"
