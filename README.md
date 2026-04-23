# Checkmate

> AI code reviewer that catches bugs, security issues, and style violations before your team does.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Deployed on Fly.io](https://img.shields.io/badge/deployed-fly.io-8b5cf6.svg)](https://checkmate-ai.fly.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Checkmate is a GitHub App that automatically reviews pull requests using Claude. It reads the diff, understands the surrounding codebase context via RAG, and posts inline comments on specific lines — like a senior engineer reviewing every PR, instantly.

**🚀 Live:** the webhook endpoint runs at [`checkmate-ai.fly.dev`](https://checkmate-ai.fly.dev). The GitHub App is installed on this repo — see it work in real time by opening a PR against `main`.

## Demo

See [PR #2](https://github.com/charanmogulla0-gith/checkmateai/pull/2) for a live example. On a deliberately vulnerable test file, the bot posted:

- A top-level review summary
- Two inline `🔴 HIGH · security` comments — one on a SQL-injection pattern, one on `eval()` of untrusted input — each on the exact offending line with a remediation suggestion

End-to-end latency from PR open → inline comments: **~15 seconds** (warm app, cached repo index).

## What It Does

- **Inline PR comments** on suspected bugs, security issues, and style violations
- **Codebase-aware** — indexes your repo so suggestions respect existing conventions
- **Production-grade observability** — every review is traced in Langfuse with cost/latency metrics
- **Eval-gated prompts** — changes to the review prompt run against a regression suite in CI
- **Self-hostable** on AWS via Terraform

## Architecture

```
GitHub PR ──webhook──▶ FastAPI ──enqueue──▶ Redis Queue ──worker──▶ Claude
                                                                      │
                            Qdrant (codebase RAG) ◀──────retrieve─────┤
                                                                      │
                            Langfuse (tracing) ◀──────instrument──────┤
                                                                      ▼
                                                         GitHub inline comments
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

## Tech Stack

| Layer | Tech | Production host |
|---|---|---|
| LLM | Claude Sonnet 4.6 (Anthropic) | Anthropic API |
| API | FastAPI + Uvicorn | Fly.io (autoscaling shared-cpu machine) |
| Queue | Redis + RQ (TLS) | Upstash |
| Vector DB | Qdrant (per-repo collections) | Qdrant Cloud |
| Metadata DB | Postgres | Neon |
| Embeddings | `BAAI/bge-small-en-v1.5` (sentence-transformers) | baked into image, CPU-only |
| Observability | Langfuse (traces, cost, latency) | Langfuse Cloud |
| Evals | promptfoo (14-case regression suite) | GitHub Actions |
| Deploy | Docker image, Fly.io with worker + app process groups | — |
| IaC (WIP) | Terraform targeting AWS ECS | — |

## Quickstart (local dev)

```bash
# 1. Clone + install
git clone https://github.com/<you>/checkmateai.git
cd checkmateai
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# 2. Start local deps (Postgres, Redis, Qdrant, Langfuse)
docker compose up -d

# 3. Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, GitHub App credentials, etc.

# 4. Run
uvicorn checkmate.main:app --reload --port 8000
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) to deploy to AWS.

## Evals

Checkmate's review prompt is regression-tested against **14 hand-curated cases** covering security (SQL injection, missing auth, path traversal, hardcoded secrets), bug categories (resource leaks, divide-by-zero, races), performance (N+1, unbounded recursion), error handling (swallowed exceptions, bad retry logic), and clean-diff false-positive checks. Run with `bash scripts/run_evals.sh`. See [`docs/EVALS.md`](docs/EVALS.md) for the full spec.

## Observability

Every review emits a Langfuse trace with:

- `claude-review` generation span (model, token usage, per-call cost, latency)
- `repo-rag` retriever span (chunks retrieved, top-score, cosine distance)
- Structured trace name `<repo>#<pr_number>` for easy filtering

## Status

🟢 **Live** — deployed and processing webhooks at [`checkmate-ai.fly.dev`](https://checkmate-ai.fly.dev). Roadmap: finish Terraform for AWS (cloud-agnostic deploy), offline repo re-indexing (remove first-PR latency), multi-model A/B via evals.

## License

MIT
