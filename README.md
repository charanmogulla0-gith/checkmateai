# Checkmate

> AI code reviewer that catches bugs, security issues, and style violations before your team does.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Checkmate is a GitHub App that automatically reviews pull requests using Claude. It reads the diff, understands the surrounding codebase context via RAG, and posts inline comments on specific lines — like a senior engineer reviewing every PR, instantly.

## Demo

<!-- TODO: add demo GIF of bot commenting on a real PR -->

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

| Layer | Tech |
|---|---|
| LLM | Claude Sonnet 4.6 (Anthropic) |
| API | FastAPI + Uvicorn |
| Queue | Redis + RQ |
| Vector DB | Qdrant (self-hosted) |
| Observability | Langfuse (self-hosted) |
| Evals | promptfoo |
| Deploy | AWS ECS Fargate + RDS + ElastiCache, Terraform IaC |
| CI | GitHub Actions |

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

Checkmate's review prompt is tested against a suite of real PRs with known issues. See [`docs/EVALS.md`](docs/EVALS.md).

## Status

Early development. Follow along or open an issue.

## License

MIT
