# Evals

Checkmate's review quality is measured against a dataset of real PRs with known issues. Every prompt change runs the eval suite in CI — regressions block the PR.

## Dataset

`evals/dataset.jsonl` — ~30 real PRs labeled with:
- `expected_findings`: list of `{severity, category, line, description_keywords}`
- `false_positive_zone`: lines the bot should NOT comment on (correct code that looks suspicious)

Sources:
- Public PRs from open-source projects (curated)
- Synthetic PRs injecting known bug patterns (null deref, SQLi, race conditions)

## Metrics

| Metric | Target |
|---|---|
| Precision (findings matching expected) | >0.7 |
| Recall (expected findings surfaced) | >0.6 |
| False positives per PR | <2 |
| P95 latency | <30s |
| Cost per PR | <$0.05 |

## Running Evals

```bash
promptfoo eval -c evals/promptfoo.yaml
promptfoo view  # local dashboard
```

## CI Integration

`.github/workflows/evals.yml` runs on every PR that touches `src/checkmate/prompts/` or `evals/`. Fails the build if precision or recall drop >5% vs main.

## Current Results

<!-- TODO: fill in after first eval run -->

| Version | Precision | Recall | Avg Cost | Avg Latency |
|---|---|---|---|---|
| v0.1.0 | - | - | - | - |
