# Architecture

## System Overview

Checkmate is an async, queue-backed GitHub App. Webhooks are received and acknowledged instantly; the actual LLM review runs in a background worker so GitHub's 10-second webhook timeout is never at risk.

## Components

### 1. Webhook Receiver (`src/checkmate/webhook.py`)
FastAPI endpoint at `POST /webhook`. Verifies the GitHub webhook HMAC signature, parses `pull_request` events (opened, synchronize, reopened), and enqueues a review job on Redis.

### 2. Review Worker (`src/checkmate/worker.py`)
RQ worker consuming the queue. For each job:
1. Fetches the PR diff via GitHub API (using installation access token)
2. Parses the unified diff into per-file hunks
3. Retrieves relevant context from Qdrant (RAG over the repo)
4. Calls Claude with a structured review prompt
5. Posts inline comments + summary comment back to the PR

### 3. Codebase Indexer (`src/checkmate/indexer.py`)
On first install (or via manual trigger), indexes the repo's source files into Qdrant. Files are chunked by AST where possible (functions, classes) and embedded with `voyage-code-3` or `text-embedding-3-small`.

### 4. Review Engine (`src/checkmate/review.py`)
Prompts Claude with:
- System prompt (review instructions, output schema)
- Repo context from RAG
- The diff itself
Uses prompt caching on the system prompt + repo conventions to keep per-review cost <$0.05.

### 5. Observability (`src/checkmate/tracing.py`)
Every review is a Langfuse trace containing: retrieval spans, LLM call with token/cost, output parsing, GitHub API calls. Enables A/B prompt comparisons and regression detection.

## Data Flow

```
PR opened/updated
        │
        ▼
GitHub webhook ───▶ FastAPI /webhook ──▶ HMAC verify ──▶ Redis queue
                                                              │
                                                              ▼
                                                         RQ worker
                                                              │
                        ┌─────────────────────────────────────┤
                        ▼                                     ▼
                   Fetch diff                          Retrieve context
                   (GitHub API)                        (Qdrant)
                        │                                     │
                        └──────────────┬──────────────────────┘
                                       ▼
                                  Claude review
                                  (with caching)
                                       │
                                       ▼
                           Parse structured output
                                       │
                                       ▼
                           Post inline comments
                           (GitHub API)
```

## Design Decisions

### Why RQ instead of Celery?
RQ is simpler, has less operational overhead, and PR volume for a single-repo bot is low. If we scale to handling many repos in parallel we'd revisit.

### Why Qdrant instead of pgvector?
Qdrant's HNSW + quantization performs better at >100k chunks, and its filtering API is cleaner for per-repo isolation. pgvector would be fine for a single-repo demo; we picked Qdrant for the production story.

### Why self-hosted Langfuse?
Avoids per-event SaaS cost during development, keeps traces in-infrastructure, and demonstrates full-stack ownership in the portfolio.

### Why prompt caching?
The system prompt + repo context (~5-20k tokens) is reused across every review. Claude's prompt caching cuts input cost by 90% on cache hits and reduces TTFT.

## Scaling Considerations

- **Multi-tenant**: add `installation_id` scoping to Qdrant collections and Langfuse traces
- **Large diffs**: chunk diffs >500 LOC across multiple Claude calls, merge findings
- **Rate limits**: respect GitHub's 5k req/hr per-installation cap via token bucket in Redis
